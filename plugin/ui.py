#!/usr/bin/env python

import os
import re
import shutil
import tempfile
from io import BytesIO

from qt.core import (
    QApplication, QDialog, QDialogButtonBox, QIcon, QMenu, QPlainTextEdit, Qt, QVBoxLayout,
)

from calibre.gui2 import Dispatcher, error_dialog, open_local_file
from calibre.gui2.actions import InterfaceAction
from calibre.gui2.threaded_jobs import ThreadedJob

from calibre_plugins.fiche_lecture_gemini.config import current_settings
from calibre_plugins.fiche_lecture_gemini.extractor import SUPPORTED_FORMATS
from calibre_plugins.fiche_lecture_gemini.i18n import all_fiche_labels

load_translations()

FICHE_ID_TYPE = 'fiche_lecture'
OLD_DATA_BASE = 'data/fiche_de_lecture'  # nom utilisé jusqu'à la version 0.2.1


def safe_name(title):
    return re.sub(r'[\\/:*?"<>|]+', '_', title or '').strip(' ._')[:100] or 'Livre'


def file_base(title, label):
    """<Titre> - <Fiche de lecture>, le libellé étant dans la langue de la fiche."""
    return f'{safe_name(title)} - {label}'


def data_relpath(title, label, ext):
    """Fichier rangé dans le dossier du livre : data/<Titre> - Fiche de lecture.<ext>"""
    return f'data/{file_base(title, label)}{ext}'


def is_fiche_relpath(relpath):
    base = relpath.rpartition('.')[0]
    return relpath.startswith('data/') and (
        base == OLD_DATA_BASE or any(base.endswith(' - ' + label) for label in all_fiche_labels()))


def fiche_book_title(title, label):
    # Le titre du livre en premier : calibre tronque les noms de fichiers longs.
    return f'{title} — {label}'


class FicheLectureAction(InterfaceAction):

    name = 'Fiche de lecture (Gemini)'
    action_spec = (_('Reading notes'), None, _('Generate reading notes with Gemini or Claude Code'), None)
    action_type = 'current'
    dont_add_to = frozenset(['context-menu-device'])

    def genesis(self):
        try:
            self.qaction.setIcon(QIcon.ic('book.png'))
        except Exception:
            pass
        menu = QMenu(self.gui)
        menu.addAction(_('Generate reading notes'), self.generate)
        menu.addAction(_('Generate with Gemini'), lambda: self.generate(provider='gemini'))
        self.claude_action = menu.addAction(_('Generate with Claude Code'),
                                            lambda: self.generate(provider='claude_code'))
        menu.addAction(_('Regenerate without using the cache'), lambda: self.generate(use_cache=False))
        menu.aboutToShow.connect(self.update_menu)
        menu.addSeparator()
        menu.addAction(_('Open the notes in the viewer'), self.open_existing)
        menu.addAction(_('Preview the chapter split'), self.preview)
        menu.addSeparator()
        menu.addAction(_('Configure…'), lambda: self.interface_action_base_plugin.do_user_config(self.gui))
        self.qaction.setMenu(menu)
        self.qaction.triggered.connect(lambda: self.generate())

    def update_menu(self):
        from calibre_plugins.fiche_lecture_gemini.claude_code import find_claude
        found = find_claude(current_settings()['claude_path'])
        self.claude_action.setEnabled(bool(found))
        self.claude_action.setText(_('Generate with Claude Code') if found
                                   else _('Generate with Claude Code (not installed)'))

    # ------------------------------------------------------------------ utils
    @property
    def db(self):
        return self.gui.current_db.new_api

    def selected_ids(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            error_dialog(self.gui, _('No book'), _('Select at least one book.'), show=True)
            return []
        return list(map(self.gui.library_view.model().id, rows))

    def copy_book(self, book_id):
        """Copie le meilleur format supporté dans un dossier temporaire."""
        fmts = {f.upper() for f in (self.db.formats(book_id) or ())}
        fmt = next((f for f in SUPPORTED_FORMATS if f in fmts), None)
        if fmt is None:
            return None, None
        tdir = tempfile.mkdtemp(prefix='fiche_lecture_')
        path = os.path.join(tdir, 'livre.' + ('epub' if fmt == 'KEPUB' else fmt.lower()))
        self.db.copy_format_to(book_id, fmt, path)
        return tdir, path

    # ------------------------------------------------------------ génération
    def generate(self, use_cache=True, provider=None):
        ids = self.selected_ids()
        if not ids:
            return
        settings = current_settings(provider)
        settings['use_cache'] = settings['use_cache'] and use_cache
        if settings['provider'] == 'claude_code':
            from calibre_plugins.fiche_lecture_gemini.claude_code import find_claude
            if not find_claude(settings['claude_path']):
                return error_dialog(self.gui, _('Claude Code not found'),
                                    _('Install Claude Code or set the path of the `claude` executable '
                                      'in the plugin configuration.'), show=True)
        elif not settings['api_key']:
            error_dialog(self.gui, _('Missing API key'),
                         _('Set your Gemini API key in the plugin settings.'), show=True)
            self.interface_action_base_plugin.do_user_config(self.gui)
            return

        from calibre_plugins.fiche_lecture_gemini.summarizer import run_fiche
        skipped = []
        for book_id in ids:
            mi = self.db.get_metadata(book_id)
            tdir, path = self.copy_book(book_id)
            if path is None:
                skipped.append(mi.title)
                continue
            meta = {'book_id': book_id, 'title': mi.title, 'authors': ' & '.join(mi.authors or []),
                    'tdir': tdir}
            engine = 'Claude Code' if settings['provider'] == 'claude_code' else 'Gemini'
            job = ThreadedJob('fiche_lecture_gemini',
                              _('Reading notes ({engine}): {title}').format(engine=engine, title=mi.title),
                              run_fiche,
                              (path, meta, settings), {}, Dispatcher(self.job_done),
                              max_concurrent_count=1, killable=True)
            job._fiche_meta = meta
            self.gui.job_manager.run_threaded_job(job)
        if skipped:
            error_dialog(self.gui, _('Unsupported format'),
                         _('These books have no EPUB, KEPUB or AZW3 format (convert them first):'),
                         det_msg='\n'.join(skipped), show=True)
        started = len(ids) - len(skipped)
        if started:
            self.gui.status_bar.show_message(
                ngettext('Reading notes: {count} job started', 'Reading notes: {count} jobs started',
                         started).format(count=started), 3000)

    def job_done(self, job):
        meta = getattr(job, '_fiche_meta', {})
        shutil.rmtree(meta.get('tdir', ''), ignore_errors=True)
        if job.failed:
            return self.gui.job_exception(job, dialog_title=_('Reading notes failed'))
        res = job.result
        settings = current_settings()
        html, md, epub = res['html'].encode('utf-8'), res['markdown'].encode('utf-8'), res['epub']
        label = res.get('fiche_label') or all_fiche_labels()[0]

        if settings['save_in_book_folder']:
            try:
                files = {data_relpath(res['title'], label, ext): BytesIO(data)
                         for ext, data in (('.html', html), ('.md', md), ('.epub', epub))}
                stale = [ef.relpath for ef in self.db.list_extra_files(res['book_id'])
                         if is_fiche_relpath(ef.relpath) and ef.relpath not in files]
                if stale:  # anciens noms (fiche_de_lecture.*), titre ou langue modifiés depuis
                    self.db.remove_extra_files(res['book_id'], stale, permanent=True)
                self.db.add_extra_files(res['book_id'], files)
            except Exception as e:
                error_dialog(self.gui, _('Saving'), _('Could not save in the book folder.'),
                             det_msg=str(e), show=True)

        if settings['output_dir']:
            base = os.path.join(settings['output_dir'], file_base(res['title'], label))
            os.makedirs(settings['output_dir'], exist_ok=True)
            for ext, data in (('.html', html), ('.md', md), ('.epub', epub)):
                with open(base + ext, 'wb') as f:
                    f.write(data)

        fiche_id = self.add_fiche_as_book(res, epub, label) if settings['add_as_book'] else None

        self.gui.status_bar.show_message(
            _('Reading notes for “{title}” ready ({engine}): {chapters} chapters, {calls} calls').format(
                title=res['title'], engine=res['engine'], chapters=res['chapters'], calls=res['api_calls']), 8000)
        if settings['open_after']:
            self.open_fiche(res['book_id'], fiche_id, epub)

    # ------------------------------------------------------------ livre « fiche »
    def find_fiche_book(self, book_id):
        """Livre « Fiche de lecture » déjà créé pour ce livre (identifiant fiche_lecture:<id>)."""
        idmap = self.db.all_field_for('identifiers', self.db.all_book_ids())
        return next((bid for bid, ids in idmap.items() if ids.get(FICHE_ID_TYPE) == str(book_id)), None)

    def add_fiche_as_book(self, res, epub, label):
        """Ajoute la fiche EPUB comme livre (ou remplace l'EPUB de la fiche existante). Retourne son id."""
        from calibre.ebooks.metadata.book.base import Metadata
        from calibre.utils.localization import canonicalize_lang
        book_id = res['book_id']
        lang = canonicalize_lang(res.get('language') or '')
        lang = lang if lang and lang != 'und' else None
        fd, path = tempfile.mkstemp(suffix='.epub', prefix='fiche_lecture_')
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(epub)
            fiche_id = self.find_fiche_book(book_id)
            if fiche_id is not None:
                new_title = fiche_book_title(res['title'], label)
                if self.db.field_for('title', fiche_id) != new_title:
                    self.db.set_field('title', {fiche_id: new_title})  # renomme aussi dossier et fichier
                    old_tags = set(all_fiche_labels())
                    tags = [t for t in self.db.field_for('tags', fiche_id) if t not in old_tags] + [label]
                    self.db.set_field('tags', {fiche_id: tags})
                    if lang:
                        self.db.set_field('languages', {fiche_id: [lang]})
                self.db.add_format(fiche_id, 'EPUB', path, replace=True)
                self.gui.library_view.model().refresh_ids([fiche_id])
            else:
                src = self.db.get_metadata(book_id)
                mi = Metadata(fiche_book_title(res['title'], label), src.authors or [_('Unknown')])
                mi.tags = [label]
                mi.languages = [lang] if lang else src.languages
                mi.set_identifier(FICHE_ID_TYPE, str(book_id))
                ids, _dups = self.db.add_books([(mi, {'EPUB': path})], add_duplicates=True)
                fiche_id = ids[0]
                self.gui.library_view.model().books_added(len(ids))
                self.gui.refresh_cover_browser()
            try:
                self.gui.library_view.select_rows([fiche_id])
            except Exception:
                pass
            return fiche_id
        except Exception as e:
            error_dialog(self.gui, _('Adding to the library'), _('Could not add the notes as a book.'),
                         det_msg=str(e), show=True)
            return None
        finally:
            os.remove(path)

    def open_fiche(self, book_id, fiche_id=None, epub=None):
        """Ouvre la fiche dans la liseuse de calibre (livre fiche, sinon EPUB du dossier, sinon HTML)."""
        view = self.gui.iactions['View']
        if fiche_id is None:
            fiche_id = self.find_fiche_book(book_id)
        if fiche_id is not None and self.db.has_format(fiche_id, 'EPUB'):
            return view.view_format_by_id(fiche_id, 'EPUB')
        path = self.extra_file_path(book_id, '.epub')
        if path is None and epub is not None:
            fd, path = tempfile.mkstemp(suffix='.epub', prefix='fiche_lecture_')
            with os.fdopen(fd, 'wb') as f:
                f.write(epub)
        if path:
            return view._view_file(path)
        path = self.extra_file_path(book_id, '.html')
        if path:
            return open_local_file(path)
        error_dialog(self.gui, _('No notes'), _('This book has no reading notes yet.'), show=True)

    # ------------------------------------------------------------ autres actions
    def extra_file_path(self, book_id, ext='.html'):
        for ef in self.db.list_extra_files(book_id):
            if is_fiche_relpath(ef.relpath) and ef.relpath.endswith(ext):
                return ef.file_path
        return None

    def open_existing(self):
        ids = self.selected_ids()
        if ids:
            self.open_fiche(ids[0])

    def preview(self):
        ids = self.selected_ids()
        if not ids:
            return
        from calibre_plugins.fiche_lecture_gemini.extractor import extract_chapters
        s = current_settings()
        tdir, path = self.copy_book(ids[0])
        if path is None:
            return error_dialog(self.gui, _('Unsupported format'), _('EPUB, KEPUB or AZW3 required.'), show=True)
        logs = []
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            chapters = extract_chapters(path, s['toc_depth'], s['min_chapter_chars'], s['skip_titles_regex'],
                                        log=logs.append)
        except Exception as e:
            return error_dialog(self.gui, _('Splitting error'), str(e), show=True)
        finally:
            QApplication.restoreOverrideCursor()
            shutil.rmtree(tdir, ignore_errors=True)

        total = sum(len(c.text) for c in chapters)
        lines = [_('{number:3d}. {title}  —  {chars:,} characters').format(number=i, title=c.title, chars=len(c.text))
                 for i, c in enumerate(chapters, 1)]
        lines += ['', _('{sections} sections, {chars:,} characters (≈ {tokens:,} tokens)').format(
            sections=len(chapters), chars=total, tokens=total // 4)]
        if logs:
            lines += ['', _('Log:')] + logs
        d = QDialog(self.gui)
        d.setWindowTitle(_('Chapter split'))
        v = QVBoxLayout(d)
        t = QPlainTextEdit('\n'.join(lines))
        t.setReadOnly(True)
        v.addWidget(t)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(d.reject)
        v.addWidget(bb)
        d.resize(700, 500)
        d.exec()
