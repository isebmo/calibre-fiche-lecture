# Fiche de lecture — extension calibre (Gemini / Claude Code)

[![Dernière version](https://img.shields.io/github/v/release/isebmo/calibre-fiche-lecture?label=version&color=8b2e2e)](https://github.com/isebmo/calibre-fiche-lecture/releases/latest)
[![Licence MIT](https://img.shields.io/github/license/isebmo/calibre-fiche-lecture?color=3a5a40)](LICENSE)
[![calibre ≥ 6.18](https://img.shields.io/badge/calibre-%E2%89%A5%206.18-5b4636)](https://calibre-ebook.com/)

> **Une fiche de lecture complète — introduction, résumé chapitre par chapitre, analyse critique — pour n'importe quel livre de votre bibliothèque calibre, en un clic.**

### 👉 [Découvrir le site de présentation](https://isebmo.github.io/calibre-fiche-lecture/) · [Télécharger la dernière version](https://github.com/isebmo/calibre-fiche-lecture/releases/latest)

L'extension découpe le livre sélectionné en chapitres d'après sa table des matières, fait résumer chaque chapitre
par une IA, puis rédige une introduction et une analyse critique. Le résultat est enregistré en **Markdown**,
**HTML** et **EPUB 3**, ajouté à votre bibliothèque comme un livre (« *Titre* — Fiche de lecture ») et ouvert
dans la liseuse de calibre.

Deux moteurs au choix :
- **Google Gemini** — API, clé gratuite à créer sur [Google AI Studio](https://aistudio.google.com/apikey) ;
- **Claude Code** — la CLI `claude` installée sur votre ordinateur, avec le compte déjà connecté : aucune clé à saisir.

---

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Installation](#installation)
- [Configuration des moteurs](#configuration-des-moteurs)
- [Langues](#langues)
- [Fonctionnement](#fonctionnement)
- [Compiler depuis les sources](#compiler-depuis-les-sources)
- [Limites](#limites)
- [English summary](#english-summary)
- [Licence](#licence)

## Fonctionnalités

La fiche contient :

1. **Introduction** : présentation, résumé d'ensemble, thèmes, personnages ou notions clés ;
2. **Résumé chapitre par chapitre** ;
3. **Analyse critique** : points forts, limites, style, portée, public visé, appréciation.

Et autour :

- 📚 **Formats** EPUB, KEPUB et AZW3 ; découpage d'après la **table des matières** (profondeur réglable).
- 🔎 **Prévisualiser le découpage** avant de consommer du quota.
- ⚙️ **Tâche de fond** calibre : annulable, progression visible dans la liste des tâches.
- 💾 **Cache des réponses** : si la génération échoue au chapitre 30, la relance repart de là.
- 📖 **Trois formats de sortie** : HTML (écran), Markdown (édition), EPUB 3 (liseuse, avec table des matières).
- 🗂️ **Livre-fiche** ajouté à la bibliothèque et ouvert dans la liseuse ; une régénération le remplace.
- ✍️ **Prompts modifiables** dans les réglages.
- 🌍 **Interface** en anglais et en français ; **fiche** en français, anglais, espagnol, allemand, italien,
  portugais… ou toute autre langue saisie librement.

## Installation

1. Téléchargez `fiche_lecture_gemini.zip` depuis la page
   [**Releases**](https://github.com/isebmo/calibre-fiche-lecture/releases/latest) (ne le décompressez pas).
2. Dans calibre : **Préférences ▸ Extensions ▸ Charger une extension depuis un fichier**, puis choisissez le zip.
3. **Redémarrez calibre.**
4. Si le bouton « Fiche de lecture » n'apparaît pas, ajoutez-le à la barre d'outils :
   **Préférences ▸ Barres d'outils et menus**.

Ensuite : sélectionnez un livre, cliquez sur **Fiche de lecture**. Le menu déroulant du bouton propose aussi
« Générer avec Gemini », « Générer avec Claude Code », « Régénérer sans utiliser le cache »,
« Ouvrir la fiche dans la liseuse », « Prévisualiser le découpage » et « Configurer… ».

Version minimale : **calibre 6.18** (Windows, macOS, Linux).

## Configuration des moteurs

| | Gemini | Claude Code |
|---|---|---|
| Authentification | clé API (réglages ou variable `GEMINI_API_KEY`) | compte déjà connecté dans Claude Code |
| Modèle | `gemini-2.5-flash` par défaut, bouton « Lister les modèles » | `sonnet` par défaut (`opus`, `haiku`, nom complet) |
| Appel | REST `generateContent` | `claude -p --tools "" --system-prompt … --output-format json`, texte sur stdin, dossier temporaire vide |

- **Gemini** : créez une clé sur <https://aistudio.google.com/apikey> et collez-la dans la configuration de
  l'extension. Le bouton « Lister les modèles » vérifie la clé. L'intervalle entre requêtes et les nouvelles
  tentatives (429/5xx) respectent le quota.
- **Claude Code** : rien à configurer si la CLI `claude` est installée et connectée. Elle est détectée
  automatiquement (`PATH`, `~/.local/bin`, `~/.claude/local`, Homebrew, npm…) ; un chemin peut être forcé
  dans les réglages. Claude est appelé **sans aucun outil**, dans un dossier temporaire vide.
- Le moteur **Automatique** choisit Gemini si une clé est configurée, sinon Claude Code s'il est détecté.

## Langues

Deux réglages indépendants :

- **Langue de l'interface** (menus, réglages, messages, journal des tâches) : elle suit celle de calibre.
  Les textes source sont en anglais, avec une traduction française (`plugin/translations/fr.po`).
- **Langue de la fiche** (onglet Sortie) : par défaut, celle de l'interface. En français, anglais, espagnol,
  allemand, italien et portugais, elle traduit les titres de la fiche (« Reading Notes », « Critical analysis »…),
  l'étiquette et le titre du livre-fiche, le nom des fichiers, l'attribut de langue de l'EPUB et les prompts.
  On peut aussi saisir une autre langue (« Nederlands », « 日本語 ») : les prompts et titres anglais sont alors
  utilisés, et la rédaction est demandée dans cette langue.
- Les prompts non modifiés suivent la langue de la fiche. Un prompt modifié est conservé tel quel.

Pour ajouter une langue d'interface : `cp plugin/translations/messages.pot plugin/translations/de.po`,
traduire, puis `./build.sh`. Après une modification des textes dans le code, `./build.sh --pot` met à jour
le modèle et les `.po`.

## Fonctionnement

### Pipeline

```
Livre ─► extractor ─► [chapitre 1 … chapitre N]
                         │   (chapitre trop long ► parties ► notes ► fusion)
                         ▼
               IA : résumé de chaque chapitre      (« map », parallélisable, mis en cache)
                         ▼
               IA : introduction  ◄── tous les résumés   (« reduce »)
               IA : analyse critique ◄── tous les résumés
                         ▼
               Markdown + HTML + EPUB ─► dossier du livre (data/<Titre> - Fiche de lecture.*)
                                       ─► dossier d'export (facultatif)
                                       ─► livre « <Titre> — Fiche de lecture » ouvert dans la liseuse calibre
```

### Découpage en chapitres

- La **table des matières** donne les points de coupure (fichier + ancre), jusqu'à la profondeur réglée (2 par défaut).
- Le texte est extrait dans l'**ordre de lecture** (spine) ; chaque point de coupure ouvre une nouvelle section,
  y compris au milieu d'un fichier.
- Les sections parasites (copyright, sommaire, bibliographie…) sont filtrées par une regex modifiable.
- Les sections trop courtes (ex. page « Partie I ») sont **fusionnées avec la suivante** (« Partie 1 — Chapitre 1 »).
- Sans table des matières : une section par fichier HTML, titrée d'après le premier `h1`-`h3`.

### Formats de sortie

- **HTML** (lecture à l'écran), **Markdown** (édition), **EPUB** (liseuse : page de titre, Introduction,
  un fichier par chapitre regroupés dans la table des matières, Analyse critique).
- Par défaut, l'EPUB devient un **livre de la bibliothèque** (« <Titre> — Fiche de lecture », étiquette
  « Fiche de lecture » — dans la langue de la fiche —, identifiant `fiche_lecture:<id du livre source>`) et
  s'ouvre dans la **liseuse de calibre**. Une régénération remplace l'EPUB de ce livre-fiche au lieu d'en créer un nouveau.

### Robustesse

- Exécution en **tâche de fond** calibre (annulable, progression dans la liste des tâches).
- Respect du quota : intervalle minimal entre requêtes, nouvelles tentatives sur 429/5xx avec le délai indiqué par l'API.
- **Cache** des réponses (dossier cache de calibre) : une relance après échec ne refacture pas les chapitres
  déjà résumés. Menu « Régénérer sans utiliser le cache » pour forcer.

### Architecture

```
plugin/
├── __init__.py      Déclaration de l'extension (InterfaceActionBase)
├── ui.py            Bouton et menu dans la barre d'outils, lancement des tâches, enregistrement
├── config.py        Réglages (JSONConfig) et fenêtre de configuration (API, découpage, sortie, prompts)
├── defaults.py      Valeurs par défaut (sans Qt)
├── i18n.py          Langue de la fiche : libellés fixes, résolution de la langue, choix des prompts
├── prompts_i18n.py  Prompts intégrés en fr, en, es, de, it, pt
├── translations/    Traductions de l'interface : messages.pot (modèle), fr.po (compilé en .mo au build)
├── extractor.py     Découpage EPUB/KEPUB/AZW3 en chapitres
├── gemini.py        Moteur Gemini : client REST (urllib), quota, nouvelles tentatives, annulation
├── claude_code.py   Moteur Claude Code : `claude -p` sans outils, détection de l'exécutable, annulation
├── epub.py          Génération de la fiche en EPUB 3 (table des matières, sans dépendance)
├── mdrender.py      Rendu Markdown ► HTML
├── summarizer.py    Pipeline « map-reduce » + cache + rendu Markdown/HTML
└── cli.py           Outil de test hors interface (exclu du zip)
```

## Compiler depuis les sources

```sh
git clone https://github.com/isebmo/calibre-fiche-lecture.git
cd calibre-fiche-lecture
./build.sh              # crée fiche_lecture_gemini.zip (compile les .po en .mo)
./build.sh --install    # idem, puis installe l'extension dans calibre (calibre-customize)
./build.sh --pot        # met à jour translations/messages.pot et les .po (xgettext/msgmerge requis)
```

`msgfmt` (paquet `gettext`) est utilisé s'il est présent ; sinon, le script se rabat sur celui de calibre.

### Test en ligne de commande

```sh
calibre-debug plugin/cli.py -- "livre.epub"                                               # aperçu du découpage, sans appel API
GEMINI_API_KEY=… calibre-debug plugin/cli.py -- "livre.epub" --run                        # fiche avec Gemini
calibre-debug plugin/cli.py -- "livre.epub" --run --engine claude_code --model sonnet     # avec Claude Code
calibre-debug plugin/cli.py -- "livre.epub" --run --engine claude_code --language en      # fiche en anglais
# -> fiche_de_lecture.md / .html / .epub
```

## Limites

- Formats EPUB, KEPUB et AZW3 uniquement (convertissez les autres avec calibre). Les livres sous **DRM** sont refusés.
- Le texte du livre est envoyé au moteur choisi (Google pour Gemini, Anthropic via Claude Code) : à vous de juger
  si c'est acceptable pour vos livres.
- La qualité de la fiche dépend du modèle et de la table des matières du livre ; une fiche générée reste à relire.
- Coût indicatif : un livre de 25 chapitres ≈ 27 requêtes ; ~170 000 tokens envoyés pour un essai de 650 000 caractères.

## English summary

**Reading notes for calibre.** This calibre plugin (calibre ≥ 6.18) generates complete reading notes for the
selected EPUB/KEPUB/AZW3 book: it splits the book into chapters using its table of contents, summarizes each
chapter with **Google Gemini** (API key) or the locally installed **Claude Code** CLI (your logged-in account),
then writes an introduction and a critical analysis. Output is Markdown, HTML and EPUB 3, added to your library as
“<Title> — Reading Notes” and opened in the calibre viewer. Background job, cancellable, response cache, chapter-split
preview, editable prompts. The UI is in English (French translation included); the notes can be written in English,
French, Spanish, German, Italian, Portuguese or any other language.
Install: download the zip from [Releases](https://github.com/isebmo/calibre-fiche-lecture/releases/latest), then
*Preferences ▸ Plugins ▸ Load plugin from file*, and restart calibre. DRM-protected books are not supported.

## Licence

[MIT](LICENSE) © 2026 Sébastien Mouret
