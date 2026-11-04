#!/usr/bin/env python

from calibre.customize import InterfaceActionBase

load_translations()


class FicheLectureGeminiPlugin(InterfaceActionBase):
    name = 'Fiche de lecture (Gemini)'  # identifiant interne : ne pas traduire (réglages, barre d'outils)
    description = _('Generates complete reading notes (introduction, chapter-by-chapter summary, '
                    'critical analysis) for the selected book with Google Gemini or Claude Code.')
    supported_platforms = ['windows', 'osx', 'linux']
    author = 'Sébastien Mouret'
    version = (0, 3, 0)
    minimum_calibre_version = (6, 18, 0)

    actual_plugin = 'calibre_plugins.fiche_lecture_gemini.ui:FicheLectureAction'

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.fiche_lecture_gemini.config import ConfigWidget
        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()
