#!/usr/bin/env python
"""Construction d'un EPUB 3 de la fiche de lecture (zip + XHTML, sans dépendance).

Structure : page de titre, Introduction, un fichier par chapitre résumé, Analyse critique,
avec une table des matières (nav.xhtml + toc.ncx pour les anciennes liseuses).
"""

import time
import uuid
import zipfile
from html import escape
from io import BytesIO

from lxml import etree, html as lhtml

try:
    from calibre_plugins.fiche_lecture_gemini.mdrender import markdown_to_html_fragment
except ImportError:
    from mdrender import markdown_to_html_fragment

CSS = """body{font-family:serif;line-height:1.5;margin:0 1em}
h1{font-size:1.6em;margin-top:2em;text-align:center}
h2{font-size:1.4em;margin-top:1em;border-bottom:1px solid #999}
h3{font-size:1.15em;margin-top:1.2em}
blockquote{margin-left:1em;padding-left:.8em;border-left:3px solid #aaa;font-style:italic}
.meta{text-align:center;font-style:italic}
"""


def md_to_xhtml_fragment(md):
    """Markdown -> fragment XHTML bien formé (lxml répare et sérialise en XML)."""
    body = markdown_to_html_fragment(md)
    root = lhtml.fragment_fromstring(body or '<p></p>', create_parent='div')
    out = [escape(root.text)] if root.text else []
    out += [etree.tostring(child, method='xml', encoding='unicode') for child in root]
    return ''.join(out)


def _page(title, body, lang):
    return (f'<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
            f'lang="{lang}" xml:lang="{lang}"><head><meta charset="utf-8"/><title>{escape(title)}</title>'
            f'<link rel="stylesheet" type="text/css" href="style.css"/></head><body>{body}</body></html>')


def build_epub(meta, engine, intro, chapters, summaries, critique, language):
    """Retourne les octets d'un EPUB. chapters : objets avec .title ; summaries : textes Markdown.

    language : résultat de i18n.resolve_language() (libellés et code de langue).
    """
    L, lang = language.labels, escape(language.iso)
    title = meta.get('title', '')
    authors = meta.get('authors', '')
    book_title = f"{title} — {L['fiche']}"
    uid = f'urn:uuid:{uuid.uuid4()}'
    modified = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    # (fichier, titre de TOC, niveau, xhtml)
    pages = []
    meta_line = escape(authors) + '<br/>' if authors else ''
    generated = escape(L['generated'].format(engine=engine, date=time.strftime(L['date'])))
    pages.append(('titre.xhtml', L['title_page'], 1,
                  f'<h1>{escape(book_title)}</h1><p class="meta">{meta_line}{generated}</p>'))
    pages.append(('introduction.xhtml', L['introduction'], 1,
                  f"<h2>{escape(L['introduction'])}</h2>{md_to_xhtml_fragment(intro)}"))
    for i, (ch, summ) in enumerate(zip(chapters, summaries), 1):
        t = f'{i}. {ch.title}'
        pages.append((f'chap{i:03d}.xhtml', t, 2, f'<h2>{escape(t)}</h2>{md_to_xhtml_fragment(summ)}'))
    pages.append(('critique.xhtml', L['critique'], 1,
                  f"<h2>{escape(L['critique'])}</h2>{md_to_xhtml_fragment(critique)}"))

    # Table des matières : chapitres regroupés sous « Résumé chapitre par chapitre »
    nav, ncx, order = [], [], 0
    chap_items = [p for p in pages if p[2] == 2]
    for name, label, level, _ in pages:
        if level == 2:
            continue
        if name == 'critique.xhtml' and chap_items:
            first = chap_items[0][0]
            sub = ''.join(f'<li><a href="{n}">{escape(t)}</a></li>' for n, t, _, _ in chap_items)
            nav.append(f'<li><a href="{first}">{escape(L["chapters"])}</a><ol>{sub}</ol></li>')
            order += 1
            inner = []
            for n, t, _, _ in chap_items:
                order += 1
                inner.append(f'<navPoint id="np{order}" playOrder="{order}"><navLabel><text>{escape(t)}</text>'
                             f'</navLabel><content src="{n}"/></navPoint>')
            ncx.append(f'<navPoint id="np{order - len(chap_items)}" playOrder="{order - len(chap_items)}">'
                       f'<navLabel><text>{escape(L["chapters"])}</text></navLabel>'
                       f'<content src="{first}"/>{"".join(inner)}</navPoint>')
        order += 1
        nav.append(f'<li><a href="{name}">{escape(label)}</a></li>')
        ncx.append(f'<navPoint id="np{order}" playOrder="{order}"><navLabel><text>{escape(label)}</text>'
                   f'</navLabel><content src="{name}"/></navPoint>')

    toc = escape(L['toc'])
    nav_doc = _page(L['toc'], f'<nav epub:type="toc" id="toc"><h1>{toc}</h1><ol>{"".join(nav)}</ol></nav>', lang)
    ncx_doc = (f'<?xml version="1.0" encoding="utf-8"?>\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" '
               f'version="2005-1"><head><meta name="dtb:uid" content="{uid}"/></head>'
               f'<docTitle><text>{escape(book_title)}</text></docTitle><navMap>{"".join(ncx)}</navMap></ncx>')

    manifest = ''.join(f'<item id="p{i}" href="{n}" media-type="application/xhtml+xml"/>'
                       for i, (n, _, _, _) in enumerate(pages))
    spine = ''.join(f'<itemref idref="p{i}"/>' for i in range(len(pages)))
    creator = f'<dc:creator>{escape(authors)}</dc:creator>' if authors else ''
    opf = (f'<?xml version="1.0" encoding="utf-8"?>\n'
           f'<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid" xml:lang="{lang}">'
           f'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
           f'<dc:identifier id="uid">{uid}</dc:identifier><dc:title>{escape(book_title)}</dc:title>'
           f'{creator}<dc:language>{lang}</dc:language><dc:subject>{escape(L['fiche'])}</dc:subject>'
           f'<meta property="dcterms:modified">{modified}</meta></metadata>'
           f'<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
           f'<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
           f'<item id="css" href="style.css" media-type="text/css"/>{manifest}</manifest>'
           f'<spine toc="ncx">{spine}</spine></package>')
    container = ('<?xml version="1.0" encoding="utf-8"?>\n'
                 '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                 '<rootfiles><rootfile full-path="OEBPS/content.opf" '
                 'media-type="application/oebps-package+xml"/></rootfiles></container>')

    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr(zipfile.ZipInfo('mimetype'), 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        dz = zipfile.ZIP_DEFLATED
        z.writestr('META-INF/container.xml', container, dz)
        z.writestr('OEBPS/content.opf', opf, dz)
        z.writestr('OEBPS/nav.xhtml', nav_doc, dz)
        z.writestr('OEBPS/toc.ncx', ncx_doc, dz)
        z.writestr('OEBPS/style.css', CSS, dz)
        for name, label, _, body in pages:
            z.writestr('OEBPS/' + name, _page(label, body, lang), dz)
    return buf.getvalue()
