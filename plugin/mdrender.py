#!/usr/bin/env python
"""Conversion Markdown -> HTML.

Les extensions sont instanciées une à une, jamais par leur nom (ni via 'extra',
qui charge ses sous-extensions par nom) : dans calibre
(application figée) le registre d'extensions de python-markdown est vide et la
résolution par nom échoue.
"""

from html import escape

try:
    load_translations()
except NameError:  # hors du chargeur d'extensions calibre (cli.py)
    pass


def markdown_to_html_fragment(md, log=None):
    try:
        import markdown
        from markdown.extensions.def_list import DefListExtension
        from markdown.extensions.fenced_code import FencedCodeExtension
        from markdown.extensions.footnotes import FootnoteExtension
        from markdown.extensions.sane_lists import SaneListExtension
        from markdown.extensions.tables import TableExtension
        exts = [TableExtension(), FencedCodeExtension(), FootnoteExtension(), DefListExtension(),
                SaneListExtension()]
        return markdown.markdown(md or '', extensions=exts)
    except Exception as e:
        if log:
            log(_('Markdown conversion failed ({error}): using plain text.').format(error=e))
        return '<pre>' + escape(md or '') + '</pre>'
