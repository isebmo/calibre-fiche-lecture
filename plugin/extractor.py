#!/usr/bin/env python
"""Découpage d'un livre (EPUB / KEPUB / AZW3) en chapitres.

Stratégie :
1. On lit la table des matières (TOC) jusqu'à une profondeur donnée ; chaque
   entrée (fichier + ancre éventuelle) devient un point de coupure.
2. On parcourt tout le spine (ordre de lecture) en extrayant le texte ; chaque
   fois qu'on rencontre un point de coupure, un nouveau chapitre commence.
3. Post-traitement : on ignore les sections parasites (copyright, sommaire…) et
   on fusionne les sections trop courtes (pages de titre de « Partie I »…).
4. Sans TOC exploitable, chaque fichier du spine devient une section.
"""

import re

from calibre.ebooks.oeb.polish.container import get_container
from calibre.ebooks.oeb.polish.toc import get_toc

try:
    load_translations()
except NameError:  # hors du chargeur d'extensions calibre (cli.py)
    pass

SUPPORTED_FORMATS = ('EPUB', 'KEPUB', 'AZW3')

BLOCK_TAGS = {
    'p', 'div', 'section', 'article', 'aside', 'header', 'footer', 'blockquote',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'ul', 'ol', 'dl', 'dt', 'dd',
    'tr', 'table', 'pre', 'br', 'hr', 'figure', 'figcaption', 'body',
}
SKIP_TAGS = {'script', 'style', 'head', 'title', 'svg', 'math'}
HEADING_TAGS = {'h1', 'h2', 'h3'}


class Chapter:
    __slots__ = ('title', 'text')

    def __init__(self, title, text=''):
        self.title = title
        self.text = text

    def __repr__(self):
        return f'Chapter({self.title!r}, {len(self.text)} car.)'


def _local(tag):
    return tag.rpartition('}')[2].lower() if isinstance(tag, str) else ''


def _clean(text):
    text = text.replace('­', '')  # tirets conditionnels
    text = re.sub(r'[ \t   ]+', ' ', text)
    text = '\n'.join(line.strip() for line in text.split('\n'))
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def _collect_toc_entries(toc, max_depth):
    entries = []

    def rec(node, depth):
        for child in node.children:
            if child.dest and child.dest_exists:
                entries.append(((child.title or '').strip(), child.dest, child.frag or None))
            if depth < max_depth:
                rec(child, depth + 1)

    rec(toc, 1)
    return entries


def _ids_in(root):
    ids = set()
    for el in root.iter():
        if isinstance(el.tag, str):
            for attr in ('id', 'name'):
                v = el.get(attr)
                if v:
                    ids.add(v)
    return ids


def _walk(el, targets, emit):
    """Parcourt l'arbre en ordre de lecture ; emit(str) ou emit(('MARK', title))."""
    tag = _local(el.tag)
    if not tag or tag in SKIP_TAGS:
        return
    if targets:
        anchor = el.get('id') or (el.get('name') if tag == 'a' else None)
        if anchor and anchor in targets:
            for title in targets.pop(anchor):
                emit(('MARK', title))
    block = tag in BLOCK_TAGS
    if block:
        emit('\n')
    if el.text:
        emit(el.text)
    for child in el:
        _walk(child, targets, emit)
        if child.tail:
            emit(child.tail)
    if block:
        emit('\n')


def _first_heading(root):
    for el in root.iter():
        if _local(el.tag) in HEADING_TAGS:
            t = _clean(''.join(el.itertext()))
            if t:
                return t[:120]
    return None


def extract_chapters(path, toc_depth=2, min_chars=1500, skip_titles_regex=None, log=None):
    """Retourne une liste de Chapter (titre, texte) dans l'ordre de lecture."""
    log = log or (lambda *a: None)
    container = get_container(path, tweak_mode=True)
    spine = [name for name, _linear in container.spine_names]
    skip_re = re.compile(skip_titles_regex, re.I) if skip_titles_regex else None

    try:
        entries = _collect_toc_entries(get_toc(container), max(1, int(toc_depth)))
    except Exception as e:
        log(_('Unreadable table of contents ({error}): splitting by file.').format(error=e))
        entries = []

    # name -> {ancre ou None: [titres]}
    targets = {}
    spine_set = set(spine)
    ids_cache = {}
    for title, dest, frag in entries:
        if dest not in spine_set:
            continue
        if frag:
            if dest not in ids_cache:
                ids_cache[dest] = _ids_in(container.parsed(dest))
            if frag not in ids_cache[dest]:
                frag = None
        targets.setdefault(dest, {}).setdefault(frag, []).append(title or _('Untitled'))

    chapters = []
    use_toc = bool(targets)
    if not use_toc:
        log(_('No usable table of contents: one section per file.'))

    current = None
    buf = []

    def flush():
        if current is not None:
            current.text = _clean(''.join(buf))
            chapters.append(current)
        buf.clear()

    def emit(item):
        nonlocal current
        if isinstance(item, tuple):
            flush()
            current = Chapter(item[1])
        elif current is not None:
            buf.append(item)

    for name in spine:
        try:
            root = container.parsed(name)
        except Exception as e:
            log(_('Skipped file {name}: {error}').format(name=name, error=e))
            continue
        body = next((el for el in root.iter() if _local(el.tag) == 'body'), None)
        if body is None:
            continue
        if use_toc:
            file_targets = targets.get(name, {})
            for title in file_targets.pop(None, []):
                emit(('MARK', title))
            _walk(body, file_targets, emit)
        else:
            emit(('MARK', _first_heading(root) or _('Section {number}').format(number=len(chapters) + 1)))
            _walk(body, None, emit)
    flush()

    return _postprocess(chapters, min_chars, skip_re, log)


def _postprocess(chapters, min_chars, skip_re, log):
    kept = []
    for ch in chapters:
        if skip_re and skip_re.search(ch.title):
            log(_('Skipped section (filtered title): {title}').format(title=ch.title))
        else:
            kept.append(ch)

    # Fusion des sections trop courtes dans la suivante (ou la précédente pour la dernière).
    merged = []
    pending = None
    for ch in kept:
        if pending is not None:
            if len(pending.text) < 200:
                ch.title = f'{pending.title} — {ch.title}'
            ch.text = (pending.text + '\n\n' + ch.text).strip()
            pending = None
        if len(ch.text) < min_chars:
            pending = ch
            continue
        merged.append(ch)
    if pending is not None and pending.text.strip():
        if merged:
            merged[-1].text += '\n\n' + pending.text
        else:
            merged.append(pending)
    return merged


def split_text(text, max_chars):
    """Découpe un texte trop long en morceaux sur des fins de paragraphe."""
    if len(text) <= max_chars:
        return [text]
    parts, cur, size = [], [], 0
    for para in text.split('\n\n'):
        if size + len(para) > max_chars and cur:
            parts.append('\n\n'.join(cur))
            cur, size = [], 0
        while len(para) > max_chars:  # paragraphe géant (rare)
            parts.append(para[:max_chars])
            para = para[max_chars:]
        cur.append(para)
        size += len(para) + 2
    if cur:
        parts.append('\n\n'.join(cur))
    return parts
