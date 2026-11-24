#!/usr/bin/env python
# Valeurs par défaut et prompts de l'extension. Aucun import Qt ici :
# ce module est aussi utilisé par l'outil en ligne de commande (cli.py).

PLUGIN_NAME = 'Fiche de lecture (Gemini)'
PREFS_NAMESPACE = 'plugins/fiche_lecture_gemini'

# Ancienne valeur par défaut (0.2.x), remplacée automatiquement si l'utilisateur ne l'a pas modifiée
OLD_SKIP_TITLES_REGEXES = [
    r"^\s*(copyright|table des mati[eè]res|sommaire|contents|table of contents|index|"
    r"couverture|cover|page de titre|title page|du m[eê]me auteur|dans la m[eê]me collection|"
    r"also by|notes?|bibliographie|bibliography|cr[ée]dits?|achev[ée] d'imprimer)\s*$",
]

SKIP_TITLES_REGEX = (
    r"^\s*(copyright|table des mati[eè]res|sommaire|contents|table of contents|index|"
    r"couverture|cover|page de titre|title page|du m[eê]me auteur|dans la m[eê]me collection|"
    r"also by|notes?|bibliographie|bibliography|cr[ée]dits?|achev[ée] d'imprimer|"
    r"[íi]ndice|sum[aá]rio|sumario|portada|inhalt|inhaltsverzeichnis|titelseite|impressum|"
    r"anmerkungen|literaturverzeichnis|frontespizio|notas|bibliograf[ií]a|cr[ée]ditos|crediti)\s*$"
)

DEFAULTS = {
    # Moteur : 'auto' (Gemini si une clé est configurée, sinon Claude Code s'il est installé),
    # 'gemini' ou 'claude_code'
    'provider': 'auto',
    # Claude Code
    'claude_path': '',          # vide = détection automatique
    'claude_model': 'sonnet',   # sonnet / opus / haiku / nom complet / vide = défaut de Claude Code
    'claude_extra_args': '',
    'claude_timeout': 900,
    # Gemini
    'api_key': '',
    'model': 'gemini-2.5-flash',
    'temperature': 0.4,
    # Clé Gemini du niveau gratuit : une requête à la fois, espacées (quota ≈ 10 req/min)
    'gemini_free_tier': False,
    # Requêtes simultanées (Claude Code, Gemini payant). Ignoré en mode Gemini gratuit.
    'parallel_requests': 6,
    'max_retries': 6,
    'request_timeout': 300,
    'use_cache': True,
    # Découpage
    'toc_depth': 2,
    'min_chapter_chars': 1500,
    'max_chunk_chars': 150000,
    'skip_titles_regex': SKIP_TITLES_REGEX,
    # Sortie
    'language': '',            # '' = langue de l'interface calibre ; sinon code ('en') ou nom libre
    'save_in_book_folder': True,
    'output_dir': '',
    'open_after': True,
    'add_as_book': True,       # ajoute la fiche EPUB comme livre de la bibliothèque (ouverte dans la liseuse)
    # Prompts : '' = prompt intégré dans la langue de la fiche (voir prompts_i18n.py)
    'system_prompt': '',
    'chapter_prompt': '',
    'part_prompt': '',
    'merge_prompt': '',
    'intro_prompt': '',
    'critique_prompt': '',
}

# Mode « Gemini gratuit »
FREE_TIER_PARALLEL = 1
FREE_TIER_INTERVAL = 6.0   # secondes entre deux requêtes

# Version des réglages enregistrés (migration des anciennes valeurs par défaut, voir config.py)
SETTINGS_VERSION = 2

PROMPT_KEYS = ['system_prompt', 'chapter_prompt', 'part_prompt', 'merge_prompt', 'intro_prompt',
               'critique_prompt']
