#!/usr/bin/env python
"""Langue de la fiche produite : libellés fixes et prompts intégrés, par langue.

La langue de l'interface (menus, réglages, messages) suit celle de calibre via gettext
(translations/*.mo). La langue de la fiche est un réglage distinct : on peut avoir calibre
en français et produire une fiche en anglais. Aucun import Qt ici (utilisé aussi par cli.py).
"""

from types import SimpleNamespace

try:
    from calibre_plugins.fiche_lecture_gemini import prompts_i18n as P
except ImportError:
    import prompts_i18n as P

# code : nom natif (aussi la valeur de {language} dans les prompts)
LANGUAGE_NAMES = {
    'fr': 'français',
    'en': 'English',
    'es': 'español',
    'de': 'Deutsch',
    'it': 'italiano',
    'pt': 'português',
}

LABELS = {
    'fr': {
        'fiche': 'Fiche de lecture',
        'introduction': 'Introduction',
        'chapters': 'Résumé chapitre par chapitre',
        'critique': 'Analyse critique',
        'title_page': 'Titre',
        'toc': 'Table des matières',
        'authors': 'Auteur(s)',
        'generated': 'Fiche générée avec {engine} — {date}',
        'part': 'Partie',
        'date': '%d/%m/%Y',
    },
    'en': {
        'fiche': 'Reading Notes',
        'introduction': 'Introduction',
        'chapters': 'Chapter-by-chapter summary',
        'critique': 'Critical analysis',
        'title_page': 'Title page',
        'toc': 'Contents',
        'authors': 'Author(s)',
        'generated': 'Generated with {engine} — {date}',
        'part': 'Part',
        'date': '%Y-%m-%d',
    },
    'es': {
        'fiche': 'Ficha de lectura',
        'introduction': 'Introducción',
        'chapters': 'Resumen capítulo por capítulo',
        'critique': 'Análisis crítico',
        'title_page': 'Portada',
        'toc': 'Índice',
        'authors': 'Autor(es)',
        'generated': 'Ficha generada con {engine} — {date}',
        'part': 'Parte',
        'date': '%d/%m/%Y',
    },
    'de': {
        'fiche': 'Lesenotizen',
        'introduction': 'Einleitung',
        'chapters': 'Zusammenfassung Kapitel für Kapitel',
        'critique': 'Kritische Analyse',
        'title_page': 'Titelseite',
        'toc': 'Inhaltsverzeichnis',
        'authors': 'Autor(en)',
        'generated': 'Erstellt mit {engine} — {date}',
        'part': 'Teil',
        'date': '%d.%m.%Y',
    },
    'it': {
        'fiche': 'Scheda di lettura',
        'introduction': 'Introduzione',
        'chapters': 'Riassunto capitolo per capitolo',
        'critique': 'Analisi critica',
        'title_page': 'Frontespizio',
        'toc': 'Indice',
        'authors': 'Autore/i',
        'generated': 'Scheda generata con {engine} — {date}',
        'part': 'Parte',
        'date': '%d/%m/%Y',
    },
    'pt': {
        'fiche': 'Ficha de leitura',
        'introduction': 'Introdução',
        'chapters': 'Resumo capítulo a capítulo',
        'critique': 'Análise crítica',
        'title_page': 'Página de rosto',
        'toc': 'Índice',
        'authors': 'Autor(es)',
        'generated': 'Ficha gerada com {engine} — {date}',
        'part': 'Parte',
        'date': '%d/%m/%Y',
    },
}

PROMPTS = P.PROMPTS
FALLBACK = 'en'  # libellés et prompts utilisés pour une langue saisie librement (ex. « japonais »)

ALIASES = {
    'fr': ['français', 'francais', 'french', 'francés', 'französisch', 'francese', 'francês', 'fra', 'fre'],
    'en': ['english', 'anglais', 'inglés', 'ingles', 'englisch', 'inglese', 'inglês', 'eng'],
    'es': ['español', 'espanol', 'spanish', 'espagnol', 'spanisch', 'spagnolo', 'espanhol', 'castellano', 'spa'],
    'de': ['deutsch', 'german', 'allemand', 'alemán', 'aleman', 'tedesco', 'alemão', 'deu', 'ger'],
    'it': ['italiano', 'italian', 'italien', 'italienisch', 'ita'],
    'pt': ['português', 'portugues', 'portuguese', 'portugais', 'portugués', 'portugiesisch', 'portoghese', 'por'],
}
_ALIAS = {a: code for code, names in ALIASES.items() for a in names + [code]}


def interface_language():
    """Code à 2 lettres de la langue de l'interface calibre ('en' hors calibre)."""
    try:
        from calibre.utils.localization import get_lang
        return (get_lang() or 'en').split('_')[0].lower()
    except Exception:
        return 'en'


def _iso639_1(value):
    """Code ISO 639-1 d'un nom de langue quelconque, via calibre si possible."""
    try:
        from calibre.utils.localization import canonicalize_lang, lang_as_iso639_1
        c = canonicalize_lang(value)
        return (c and lang_as_iso639_1(c)) or c
    except Exception:
        return None


def resolve_language(value):
    """Réglage « langue de la fiche » -> SimpleNamespace(code, name, iso, labels).

    value : '' (langue de l'interface calibre), un code ('en') ou un nom libre ('English', 'japonais').
    code : jeu de libellés/prompts utilisé ; name : valeur de {language} ; iso : attribut lang de l'EPUB.
    """
    v = (value or '').strip() or interface_language()
    code = _ALIAS.get(v.lower())
    if code:
        return SimpleNamespace(code=code, name=LANGUAGE_NAMES[code], iso=code, labels=LABELS[code])
    iso = _iso639_1(v) or (v.lower() if 2 <= len(v) <= 3 and v.isalpha() else 'und')
    if iso in LABELS:
        return SimpleNamespace(code=iso, name=LANGUAGE_NAMES[iso], iso=iso, labels=LABELS[iso])
    return SimpleNamespace(code=FALLBACK, name=v, iso=iso, labels=LABELS[FALLBACK])


def is_builtin_prompt(key, text):
    t = (text or '').strip()
    return any(t == prompts[key].strip() for prompts in PROMPTS.values())


def effective_prompt(key, stored, code):
    """Prompt personnalisé s'il y en a un, sinon le prompt intégré de la langue de la fiche."""
    if stored and stored.strip() and not is_builtin_prompt(key, stored):
        return stored
    return PROMPTS.get(code, PROMPTS[FALLBACK])[key]


def all_fiche_labels():
    """« Fiche de lecture » dans toutes les langues (reconnaissance des fichiers déjà produits)."""
    return [lab['fiche'] for lab in LABELS.values()]
