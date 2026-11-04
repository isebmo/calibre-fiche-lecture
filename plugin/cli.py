#!/usr/bin/env python
"""Outil de test hors interface graphique.

  calibre-debug cli.py -- livre.epub              # aperçu du découpage (aucun appel API)
  calibre-debug cli.py -- livre.epub --run        # génère la fiche (GEMINI_API_KEY requis)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from defaults import DEFAULTS  # noqa: E402
from extractor import extract_chapters  # noqa: E402


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('book')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--engine', choices=['gemini', 'claude_code'], default='gemini')
    ap.add_argument('--model', help='modèle Gemini ou Claude (sonnet, opus, haiku…)')
    ap.add_argument('--toc-depth', type=int, default=DEFAULTS['toc_depth'])
    ap.add_argument('--min-chars', type=int, default=DEFAULTS['min_chapter_chars'])
    ap.add_argument('--language', default='', help='langue de la fiche : fr, en, es, de, it, pt ou nom libre '
                    "(défaut : langue de l'interface calibre)")
    ap.add_argument('--out', default='fiche_de_lecture')
    a = ap.parse_args(argv)

    if not a.run:
        chs = extract_chapters(a.book, a.toc_depth, a.min_chars, DEFAULTS['skip_titles_regex'], log=print)
        for i, c in enumerate(chs, 1):
            print(f'{i:3d}. {c.title[:70]:70s} {len(c.text):>8,} car.  « {c.text[:60]!r} »')
        print(f'\n{len(chs)} sections, {sum(len(c.text) for c in chs):,} caractères')
        return

    from summarizer import run_fiche
    settings = dict(DEFAULTS, api_key=os.environ.get('GEMINI_API_KEY', ''), provider=a.engine,
                    toc_depth=a.toc_depth, min_chapter_chars=a.min_chars, language=a.language)
    if a.model:
        settings['claude_model' if a.engine == 'claude_code' else 'model'] = a.model
    from calibre.ebooks.metadata.meta import get_metadata
    with open(a.book, 'rb') as f:
        mi = get_metadata(f, os.path.splitext(a.book)[1][1:].lower())
    authors = ' & '.join(x for x in (mi.authors or []) if x and not x.startswith('Inconnu') and x != 'Unknown')
    res = run_fiche(a.book, {'title': mi.title or os.path.basename(a.book), 'authors': authors}, settings)
    for ext, key in (('md', 'markdown'), ('html', 'html'), ('epub', 'epub')):
        data = res[key]
        with open(f'{a.out}.{ext}', 'wb') as f:
            f.write(data if isinstance(data, bytes) else data.encode('utf-8'))
    print(f'Écrit : {a.out}.md / .html / .epub ({res["engine"]})')


if __name__ == '__main__':
    main(sys.argv[1:])
