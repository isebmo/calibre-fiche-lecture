#!/usr/bin/env python
"""Pipeline : découpage -> résumé de chaque chapitre -> introduction + critique -> document.

Exécuté dans un thread de fond (ThreadedJob de calibre) ou via cli.py.
"""

import hashlib
import html
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    load_translations()
except NameError:  # hors du chargeur d'extensions calibre (cli.py)
    pass

try:
    from calibre_plugins.fiche_lecture_gemini.extractor import extract_chapters, split_text
    from calibre_plugins.fiche_lecture_gemini.i18n import effective_prompt, resolve_language
    from calibre_plugins.fiche_lecture_gemini.claude_code import ClaudeCodeClient
    from calibre_plugins.fiche_lecture_gemini.epub import build_epub
    from calibre_plugins.fiche_lecture_gemini.mdrender import markdown_to_html_fragment
    from calibre_plugins.fiche_lecture_gemini.gemini import GeminiClient
except ImportError:  # exécution hors calibre GUI (cli.py)
    from claude_code import ClaudeCodeClient
    from epub import build_epub
    from mdrender import markdown_to_html_fragment
    from extractor import extract_chapters, split_text
    from gemini import GeminiClient
    from i18n import effective_prompt, resolve_language

PROVIDERS = {'gemini': 'Gemini', 'claude_code': 'Claude Code'}


def make_client(s, should_stop, log):
    if s['provider'] == 'claude_code':
        return ClaudeCodeClient(s['claude_path'], s['claude_model'], s['claude_extra_args'],
                                max_retries=s['max_retries'], timeout=s['claude_timeout'],
                                should_stop=should_stop, log=log)
    return GeminiClient(s['api_key'], s['model'], temperature=s['temperature'], max_retries=s['max_retries'],
                        min_interval=s['min_interval'], timeout=s['request_timeout'],
                        should_stop=should_stop, log=log)


def render(template, **values):
    """Remplace {cle} sans interpréter les autres accolades du texte."""
    for k, v in values.items():
        template = template.replace('{' + k + '}', str(v))
    return template


class SummaryCache:

    def __init__(self, enabled):
        self.enabled = enabled
        self.hits = 0
        try:
            from calibre.constants import cache_dir
            self.root = os.path.join(cache_dir(), 'fiche_lecture_gemini')
        except Exception:
            self.root = None

    def _path(self, key):
        return os.path.join(self.root, key[:2], key + '.md')

    @staticmethod
    def key(*parts):
        h = hashlib.sha256()
        for p in parts:
            h.update(str(p).encode('utf-8'))
            h.update(b'\0')
        return h.hexdigest()

    def get(self, key):
        if not (self.enabled and self.root):
            return None
        try:
            with open(self._path(key), encoding='utf-8') as f:
                self.hits += 1
                return f.read()
        except OSError:
            return None

    def put(self, key, value):
        if not self.root:
            return
        path = self._path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(value)


def run_fiche(book_path, meta, settings, notifications=None, abort=None, log=None):
    t0 = time.monotonic()
    log = log or print
    abort = abort or threading.Event()
    stop = threading.Event()

    def notify(frac, msg):
        log(msg)
        if notifications is not None:
            notifications.put((frac, msg))

    lang = resolve_language(settings['language'])
    s = dict(settings)
    for key in ('system_prompt', 'chapter_prompt', 'part_prompt', 'merge_prompt', 'intro_prompt',
                'critique_prompt'):
        s[key] = effective_prompt(key, s.get(key), lang.code)
    title, authors = meta.get('title', ''), meta.get('authors', '')
    common = {'title': title, 'authors': authors, 'language': lang.name}
    system = render(s['system_prompt'], **common)

    notify(0.01, _('Splitting the book into chapters…'))
    chapters = extract_chapters(book_path, toc_depth=s['toc_depth'], min_chars=s['min_chapter_chars'],
                                skip_titles_regex=s['skip_titles_regex'], log=log)
    if not chapters:
        raise Exception(_('No chapters could be extracted from this book.'))
    total = len(chapters)
    notify(0.03, _('{sections} sections found, {chars:,} characters.').format(
        sections=total, chars=sum(len(c.text) for c in chapters)))

    client = make_client(s, lambda: abort.is_set() or stop.is_set(), log)
    notify(0.03, _('Engine: {engine} — notes language: {language}').format(engine=client.label, language=lang.name))
    try:
        return _run(s, meta, chapters, client, system, common, notify, stop, t0, lang)
    finally:
        client.close()


def _run(s, meta, chapters, client, system, common, notify, stop, t0, lang):
    title, total = common['title'], len(chapters)

    def notify_log(msg):
        notify(1.0, msg)
    cache = SummaryCache(s['use_cache'])

    def ask(prompt):
        key = cache.key(client.cache_tag, s['temperature'], system, prompt)
        cached = cache.get(key)
        if cached is not None:
            return cached
        answer = client.generate(prompt, system=system)
        cache.put(key, answer)
        return answer

    def summarize(i, ch):
        vals = dict(common, index=i + 1, total=total, chapter_title=ch.title)
        parts = split_text(ch.text, s['max_chunk_chars'])
        if len(parts) == 1:
            return ask(render(s['chapter_prompt'], text=ch.text, **vals))
        notes = [ask(render(s['part_prompt'], text=p, part=j + 1, parts=len(parts), **vals))
                 for j, p in enumerate(parts)]
        part = lang.labels['part']
        joined = '\n\n'.join(f'#### {part} {j + 1}\n{n}' for j, n in enumerate(notes))
        return ask(render(s['merge_prompt'], text=joined, **vals))

    # 1. Résumés des chapitres (« map »)
    summaries = [None] * total
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, int(s['parallel_requests']))) as ex:
        futures = {ex.submit(summarize, i, ch): i for i, ch in enumerate(chapters)}
        try:
            for fut in as_completed(futures):
                i = futures[fut]
                summaries[i] = fut.result()
                done += 1
                notify(0.03 + 0.82 * done / total, _('Summary {done}/{total}: {title}').format(
                    done=done, total=total, title=chapters[i].title))
        except BaseException:
            stop.set()
            for f in futures:
                f.cancel()
            raise

    # 2. Synthèse (« reduce ») : introduction puis critique
    digest = '\n\n'.join(f'### {i + 1}. {ch.title}\n{summ}'
                         for i, (ch, summ) in enumerate(zip(chapters, summaries)))
    notify(0.87, _('Writing the introduction…'))
    intro = ask(render(s['intro_prompt'], summaries=digest, **common))
    notify(0.94, _('Writing the critical analysis…'))
    critique = ask(render(s['critique_prompt'], summaries=digest, **common))

    markdown_doc = build_markdown(meta, client.label, chapters, summaries, intro, critique, lang)
    elapsed = time.monotonic() - t0
    cost = getattr(client, 'cost_usd', 0)
    msg = _('Done in {seconds:.0f} s ({calls} calls, {hits} cached answers').format(
        seconds=elapsed, calls=client.calls, hits=cache.hits)
    if cost:
        msg += _(', estimated cost ${cost:.2f}').format(cost=cost)
    notify(1.0, msg + ').')
    fiche = lang.labels['fiche']
    return {
        'book_id': meta.get('book_id'),
        'title': title,
        'markdown': markdown_doc,
        'html': markdown_to_html(markdown_doc, f'{title} — {fiche}', lang.iso, notify_log),
        'epub': build_epub(meta, client.label, intro, chapters, summaries, critique, lang),
        'fiche_label': fiche,
        'language': lang.iso,
        'chapters': total,
        'api_calls': client.calls,
        'engine': client.label,
        'cache_hits': cache.hits,
        'elapsed': elapsed,
    }


def build_markdown(meta, engine, chapters, summaries, intro, critique, lang):
    L = lang.labels
    sep = ' : ' if lang.code == 'fr' else ': '
    lines = [f"# {L['fiche']} — {meta.get('title', '')}", '']
    if meta.get('authors'):
        lines.append(f"**{L['authors']}**{sep}{meta['authors']}  ")
    lines += ['*' + L['generated'].format(engine=engine, date=time.strftime(L['date'])) + '*', '',
              f"## {L['introduction']}", '', intro.strip(), '',
              f"## {L['chapters']}", '']
    for i, (ch, summ) in enumerate(zip(chapters, summaries)):
        lines += [f'### {i + 1}. {ch.title}', '', summ.strip(), '']
    lines += [f"## {L['critique']}", '', critique.strip(), '']
    return '\n'.join(lines)


CSS = """
body{font-family:Georgia,'Times New Roman',serif;max-width:46em;margin:2em auto;padding:0 1em;
line-height:1.6;color:#222;background:#fdfcf8}
h1{font-size:1.8em;border-bottom:2px solid #8a6d3b;padding-bottom:.3em}
h2{font-size:1.4em;margin-top:2em;color:#5a4320;border-bottom:1px solid #ddd}
h3{font-size:1.15em;margin-top:1.5em}
blockquote{border-left:3px solid #c9b48a;margin-left:0;padding-left:1em;color:#555;font-style:italic}
@media (prefers-color-scheme:dark){body{background:#1d1c1a;color:#ddd}h2{color:#d8b97a}}
"""


def markdown_to_html(md, title, lang='fr', log=None):
    body = markdown_to_html_fragment(md, log)
    return (f'<!DOCTYPE html>\n<html lang="{html.escape(lang)}"><head><meta charset="utf-8">'
            f'<title>{html.escape(title)}</title><style>{CSS}</style></head>'
            f'<body>{body}</body></html>')
