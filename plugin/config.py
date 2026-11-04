#!/usr/bin/env python

from qt.core import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPlainTextEdit, QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from calibre.gui2 import error_dialog
from calibre.utils.config import JSONConfig

from calibre_plugins.fiche_lecture_gemini.claude_code import CLAUDE_MODELS
from calibre_plugins.fiche_lecture_gemini.defaults import (
    DEFAULTS, OLD_SKIP_TITLES_REGEXES, PREFS_NAMESPACE, PROMPT_KEYS, SKIP_TITLES_REGEX,
)
from calibre_plugins.fiche_lecture_gemini.i18n import (
    LANGUAGE_NAMES, PROMPTS, interface_language, is_builtin_prompt, resolve_language,
)

load_translations()

prefs = JSONConfig(PREFS_NAMESPACE)
prefs.defaults.update(DEFAULTS)


def provider_choices():
    return [
        ('auto', _('Automatic (Gemini if a key is configured, otherwise Claude Code)')),
        ('gemini', _('Google Gemini (API)')),
        ('claude_code', _('Claude Code (local CLI)')),
    ]


def prompt_titles():
    return {
        'system_prompt': _('System'),
        'chapter_prompt': _('Chapter'),
        'part_prompt': _('Part of a long chapter'),
        'merge_prompt': _('Merging the parts'),
        'intro_prompt': _('Introduction'),
        'critique_prompt': _('Critique'),
    }


def current_settings(provider=None):
    """Instantané des réglages (dict simple) à transmettre au thread de fond.

    Résout le moteur « auto » : Gemini si une clé est disponible, sinon Claude Code s'il est installé.
    """
    import os
    from calibre_plugins.fiche_lecture_gemini.claude_code import find_claude
    s = {k: prefs[k] for k in DEFAULTS}
    if not s['api_key']:
        s['api_key'] = os.environ.get('GEMINI_API_KEY', '')
    if s['skip_titles_regex'] in OLD_SKIP_TITLES_REGEXES:
        s['skip_titles_regex'] = SKIP_TITLES_REGEX
    s['provider'] = provider or s['provider']
    if s['provider'] == 'auto':
        s['provider'] = 'claude_code' if not s['api_key'] and find_claude(s['claude_path']) else 'gemini'
    return s


class ConfigWidget(QWidget):

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        tabs = QTabWidget(self)
        layout.addWidget(tabs)

        # --- Onglet Moteur ------------------------------------------------
        w = QWidget()
        f = QFormLayout(w)
        self.provider = QComboBox()
        for key, label in provider_choices():
            self.provider.addItem(label, key)
        self.provider.setCurrentIndex(max(0, self.provider.findData(prefs['provider'])))
        f.addRow(_('Default engine:'), self.provider)

        self.parallel = QSpinBox()
        self.parallel.setRange(1, 16)
        self.parallel.setValue(prefs['parallel_requests'])
        self.parallel.setToolTip(_('Number of chapters summarized at the same time.'))
        f.addRow(_('Parallel requests:'), self.parallel)

        self.max_retries = QSpinBox()
        self.max_retries.setRange(0, 20)
        self.max_retries.setValue(prefs['max_retries'])
        f.addRow(_('Retries:'), self.max_retries)

        self.use_cache = QCheckBox(_('Reuse summaries already generated (resume after an error)'))
        self.use_cache.setChecked(prefs['use_cache'])
        f.addRow(self.use_cache)

        # Claude Code
        f.addRow(QLabel('<b>Claude Code</b> ' + _('(uses the account signed in to Claude Code, no key needed)')))
        row = QHBoxLayout()
        self.claude_path = QLineEdit(prefs['claude_path'])
        self.claude_path.setPlaceholderText(_('automatic detection'))
        row.addWidget(self.claude_path, 1)
        b = QPushButton(_('Detect'))
        b.clicked.connect(self.detect_claude)
        row.addWidget(b)
        f.addRow(_('claude executable:'), row)
        self.claude_status = QLabel()
        self.claude_status.setWordWrap(True)
        f.addRow('', self.claude_status)
        self.claude_model = QComboBox()
        self.claude_model.setEditable(True)
        self.claude_model.addItems(CLAUDE_MODELS + [''])
        self.claude_model.setCurrentText(prefs['claude_model'])
        self.claude_model.setToolTip(_('Alias (sonnet, opus, haiku) or full name; empty = Claude Code default model.'))
        f.addRow(_('Claude model:'), self.claude_model)
        self.claude_extra = QLineEdit(prefs['claude_extra_args'])
        self.claude_extra.setPlaceholderText(_('e.g. --effort low'))
        f.addRow(_('Extra arguments:'), self.claude_extra)
        self.claude_timeout = QSpinBox()
        self.claude_timeout.setRange(60, 7200)
        self.claude_timeout.setSuffix(' s')
        self.claude_timeout.setValue(prefs['claude_timeout'])
        f.addRow(_('Max. time per request:'), self.claude_timeout)
        tabs.addTab(w, _('Engine'))
        self.detect_claude(quiet=True)

        # --- Onglet Gemini ------------------------------------------------
        w = QWidget()
        f = QFormLayout(w)
        self.api_key = QLineEdit(prefs['api_key'])
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText(_('Key from https://aistudio.google.com/apikey (or $GEMINI_API_KEY)'))
        f.addRow(_('Gemini API key:'), self.api_key)

        row = QHBoxLayout()
        self.model = QComboBox()
        self.model.setEditable(True)
        self.model.addItem(prefs['model'])
        self.model.setCurrentText(prefs['model'])
        row.addWidget(self.model, 1)
        b = QPushButton(_('List models'))
        b.setToolTip(_('Queries the API with the key entered (also checks that the key works).'))
        b.clicked.connect(self.fetch_models)
        row.addWidget(b)
        f.addRow(_('Model:'), row)

        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0, 2)
        self.temperature.setSingleStep(0.1)
        self.temperature.setValue(prefs['temperature'])
        f.addRow(_('Temperature:'), self.temperature)

        self.min_interval = QDoubleSpinBox()
        self.min_interval.setRange(0, 120)
        self.min_interval.setSuffix(' s')
        self.min_interval.setValue(prefs['min_interval'])
        self.min_interval.setToolTip(_('Minimum delay between two requests, to stay within the quota (free tier: ~4-6 s).'))
        f.addRow(_('Minimum interval:'), self.min_interval)

        tabs.addTab(w, 'Gemini')

        # --- Onglet Découpage ---------------------------------------------
        w = QWidget()
        f = QFormLayout(w)
        self.toc_depth = QSpinBox()
        self.toc_depth.setRange(1, 6)
        self.toc_depth.setValue(prefs['toc_depth'])
        self.toc_depth.setToolTip(_('1 = only the top-level entries of the table of contents.'))
        f.addRow(_('Table of contents depth:'), self.toc_depth)

        self.min_chars = QSpinBox()
        self.min_chars.setRange(0, 100000)
        self.min_chars.setSingleStep(500)
        self.min_chars.setValue(prefs['min_chapter_chars'])
        self.min_chars.setToolTip(_('Shorter sections are merged with the next one.'))
        f.addRow(_('Minimum section size (chars):'), self.min_chars)

        self.max_chunk = QSpinBox()
        self.max_chunk.setRange(10000, 2000000)
        self.max_chunk.setSingleStep(10000)
        self.max_chunk.setValue(prefs['max_chunk_chars'])
        self.max_chunk.setToolTip(_('Beyond this, the chapter is split into parts that are summarized separately, then merged.'))
        f.addRow(_('Maximum size sent at once (chars):'), self.max_chunk)

        regex = prefs['skip_titles_regex']
        self.skip_regex = QLineEdit(SKIP_TITLES_REGEX if regex in OLD_SKIP_TITLES_REGEXES else regex)
        self.skip_regex.setToolTip(_('Regular expression: sections whose title matches are skipped.'))
        f.addRow(_('Titles to skip (regex):'), self.skip_regex)
        tabs.addTab(w, _('Splitting'))

        # --- Onglet Sortie ------------------------------------------------
        w = QWidget()
        f = QFormLayout(w)
        self.language = QComboBox()
        self.language.setEditable(True)
        ui = interface_language()
        self.language.addItem(_('Same as the calibre interface ({language})').format(
            language=LANGUAGE_NAMES.get(ui, ui)), '')
        for code, name in LANGUAGE_NAMES.items():
            self.language.addItem(name, code)
        self.language.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        stored = prefs['language'].strip()
        if not stored:
            idx = 0
        elif stored in LANGUAGE_NAMES:
            idx = self.language.findData(stored)
        elif stored.lower() in (n.lower() for n in LANGUAGE_NAMES.values()) or stored.lower() == 'francais':
            idx = self.language.findData(resolve_language(stored).code)  # anciens réglages : « français »
        else:
            idx = -1
        if idx >= 0:
            self.language.setCurrentIndex(idx)
        else:
            self.language.setEditText(stored)
        self.language.setToolTip(_(
            'Language of the generated notes (headings, prompts and text written by the AI). '
            'You can also type another language, e.g. “日本語” or “Nederlands”: '
            'the English prompts are then used, asking for an answer in that language.'))
        self.language.currentTextChanged.connect(self.language_changed)
        f.addRow(_('Notes language:'), self.language)
        self.save_in_book = QCheckBox(_('Save in the book folder (calibre data files)'))
        self.save_in_book.setChecked(prefs['save_in_book_folder'])
        f.addRow(self.save_in_book)
        row = QHBoxLayout()
        self.output_dir = QLineEdit(prefs['output_dir'])
        self.output_dir.setPlaceholderText(_('(optional) also copy to this folder'))
        row.addWidget(self.output_dir, 1)
        b = QPushButton('…')
        b.clicked.connect(self.choose_dir)
        row.addWidget(b)
        f.addRow(_('Export folder:'), row)
        self.open_after = QCheckBox(_('Open the notes when generation finishes'))
        self.open_after.setChecked(prefs['open_after'])
        f.addRow(self.open_after)
        self.add_as_book = QCheckBox(_('Also add the notes (EPUB) as a book in the library'))
        self.add_as_book.setToolTip(_('Opens in the calibre viewer and can be sent to an e-reader. '
                                      'Title: “<Title> — Reading Notes” (in the notes language).'))
        self.add_as_book.setChecked(prefs['add_as_book'])
        f.addRow(self.add_as_book)
        tabs.addTab(w, _('Output'))

        # --- Onglet Prompts -----------------------------------------------
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel(_('Variables:') + ' {title} {authors} {language} {index} {total} {chapter_title} '
                           '{text} {part} {parts} {summaries}'))
        hint = QLabel(_('Unmodified prompts follow the notes language. A modified prompt is used as is, '
                        'whatever the language.'))
        hint.setWordWrap(True)
        v.addWidget(hint)
        ptabs = QTabWidget()
        self.prompts = {}
        titles = prompt_titles()
        code = self.lang_code()
        for key in PROMPT_KEYS:
            stored = prefs[key]
            ed = QPlainTextEdit(stored if stored and not is_builtin_prompt(key, stored) else PROMPTS[code][key])
            self.prompts[key] = ed
            ptabs.addTab(ed, titles[key])
        v.addWidget(ptabs)
        b = QPushButton(_('Restore the default prompts'))
        b.clicked.connect(self.reset_prompts)
        v.addWidget(b)
        tabs.addTab(w, _('Prompts'))

        self.resize(720, 560)

    # ------------------------------------------------------------------
    def language_value(self):
        idx = self.language.currentIndex()
        if idx >= 0 and self.language.currentText() == self.language.itemText(idx):
            return self.language.itemData(idx) or ''
        if not self.language.currentText().strip():
            return ''
        return self.language.currentText().strip()

    def lang_code(self):
        return resolve_language(self.language_value()).code

    def language_changed(self):
        # Les prompts non modifiés suivent la langue choisie
        code = self.lang_code()
        for key, ed in self.prompts.items():
            if is_builtin_prompt(key, ed.toPlainText()):
                ed.setPlainText(PROMPTS[code][key])

    def reset_prompts(self):
        code = self.lang_code()
        for key, ed in self.prompts.items():
            ed.setPlainText(PROMPTS[code][key])

    def choose_dir(self):
        d = QFileDialog.getExistingDirectory(self, _('Export folder'), self.output_dir.text())
        if d:
            self.output_dir.setText(d)

    def detect_claude(self, quiet=False):
        from calibre_plugins.fiche_lecture_gemini.claude_code import claude_version, find_claude
        exe = find_claude(self.claude_path.text().strip())
        if exe:
            self.claude_status.setText(f'✓ {exe} — {claude_version(exe)}')
        else:
            self.claude_status.setText('✗ ' + _('Claude Code not found') + ' (https://claude.com/claude-code)')

    def fetch_models(self):
        import os
        from calibre_plugins.fiche_lecture_gemini.gemini import list_models
        key = self.api_key.text().strip() or os.environ.get('GEMINI_API_KEY', '')
        try:
            models = list_models(key)
        except Exception as e:
            return error_dialog(self, 'Gemini', _('Could not list the models: {error}').format(error=e), show=True)
        cur = self.model.currentText()
        self.model.clear()
        self.model.addItems(sorted(models))
        self.model.setCurrentText(cur)

    def save_settings(self):
        prefs['provider'] = self.provider.currentData()
        prefs['claude_path'] = self.claude_path.text().strip()
        prefs['claude_model'] = self.claude_model.currentText().strip()
        prefs['claude_extra_args'] = self.claude_extra.text().strip()
        prefs['claude_timeout'] = self.claude_timeout.value()
        prefs['api_key'] = self.api_key.text().strip()
        prefs['model'] = self.model.currentText().strip() or DEFAULTS['model']
        prefs['temperature'] = self.temperature.value()
        prefs['parallel_requests'] = self.parallel.value()
        prefs['min_interval'] = self.min_interval.value()
        prefs['max_retries'] = self.max_retries.value()
        prefs['use_cache'] = self.use_cache.isChecked()
        prefs['toc_depth'] = self.toc_depth.value()
        prefs['min_chapter_chars'] = self.min_chars.value()
        prefs['max_chunk_chars'] = self.max_chunk.value()
        prefs['skip_titles_regex'] = self.skip_regex.text()
        prefs['language'] = self.language_value()
        prefs['save_in_book_folder'] = self.save_in_book.isChecked()
        prefs['output_dir'] = self.output_dir.text().strip()
        prefs['open_after'] = self.open_after.isChecked()
        prefs['add_as_book'] = self.add_as_book.isChecked()
        for key, ed in self.prompts.items():
            text = ed.toPlainText()
            prefs[key] = '' if is_builtin_prompt(key, text) else text  # '' = suit la langue de la fiche
