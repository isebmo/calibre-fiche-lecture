#!/usr/bin/env python
"""Moteur « Claude Code » : appelle la CLI `claude` installée localement en mode non interactif.

Utilise le compte déjà connecté dans Claude Code (abonnement Pro/Max ou clé API) :
aucune clé à saisir dans calibre. Chaque requête lance `claude -p` avec :
- le prompt sur l'entrée standard (pas de limite de longueur de ligne de commande) ;
- aucun outil (--tools ""), aucun serveur MCP, aucune commande slash : réponse texte pure ;
- un prompt système dédié (remplace celui de Claude Code, moins de tokens) ;
- un dossier de travail temporaire vide (aucun CLAUDE.md de projet n'est chargé).
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time

try:
    load_translations()
except NameError:  # hors du chargeur d'extensions calibre (cli.py)
    pass

try:
    from calibre_plugins.fiche_lecture_gemini.gemini import Aborted, GeminiError
except ImportError:
    from gemini import Aborted, GeminiError


class ClaudeCodeError(GeminiError):
    pass


NON_RETRYABLE = re.compile(r'usage limit|limit reached|not logged in|/login|invalid api key|'
                           r'authentication|credit balance|unknown option|invalid model', re.I)
CLAUDE_MODELS = ['sonnet', 'opus', 'haiku']


def _candidates():
    home = os.path.expanduser('~')
    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA', '')
        return [os.path.join(home, '.local', 'bin', 'claude.exe'),
                os.path.join(appdata, 'npm', 'claude.cmd'),
                os.path.join(home, '.claude', 'local', 'claude.exe')]
    return [os.path.join(home, '.local', 'bin', 'claude'),
            os.path.join(home, '.claude', 'local', 'claude'),
            '/opt/homebrew/bin/claude', '/usr/local/bin/claude',
            os.path.join(home, '.npm-global', 'bin', 'claude'),
            os.path.join(home, '.bun', 'bin', 'claude')]


def find_claude(configured=''):
    """Chemin de l'exécutable `claude`, ou None.

    calibre lancé depuis le Finder/Dock a un PATH minimal : on cherche aussi
    dans les emplacements d'installation habituels.
    """
    if configured:
        p = os.path.expanduser(configured)
        return p if os.path.isfile(p) else None
    found = shutil.which('claude')
    if found:
        return found
    return next((p for p in _candidates() if os.path.isfile(p) and os.access(p, os.X_OK)), None)


def _clean_env(exe):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('PYTHON', 'DYLD_', 'QT_', 'CALIBRE_')) and k != 'CLAUDECODE'}
    extra = [os.path.dirname(exe), os.path.expanduser('~/.local/bin'), '/opt/homebrew/bin', '/usr/local/bin']
    env['PATH'] = os.pathsep.join(extra + [env.get('PATH', '/usr/bin:/bin')])
    return env


def _popen_kwargs():
    if sys.platform == 'win32':
        return {'creationflags': 0x08000000}  # CREATE_NO_WINDOW
    return {}


def claude_version(exe):
    try:
        out = subprocess.run([exe, '--version'], capture_output=True, text=True, timeout=30,
                             env=_clean_env(exe), **_popen_kwargs())
        return out.stdout.strip() or out.stderr.strip()
    except Exception as e:
        return _('error: {error}').format(error=e)


class ClaudeCodeClient:

    def __init__(self, exe='', model='sonnet', extra_args='', max_retries=4, timeout=900,
                 should_stop=None, log=None):
        self.exe = find_claude(exe)
        if not self.exe:
            raise ClaudeCodeError(_('The `claude` executable (Claude Code) was not found. '
                                    'Install it or set its path in the configuration.'))
        self.model = model.strip()
        self.extra_args = shlex.split(extra_args or '')
        self.max_retries = max_retries
        self.timeout = timeout
        self.should_stop = should_stop or (lambda: False)
        self.log = log or (lambda *a: None)
        self.label = f"Claude Code ({self.model or _('default model')})"
        self.cache_tag = f'claude-code:{self.model}'
        self.calls = 0
        self.cost_usd = 0.0
        self._lock = threading.Lock()
        self.workdir = tempfile.mkdtemp(prefix='fiche_lecture_claude_')

    def _sleep(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if self.should_stop():
                raise Aborted()
            time.sleep(min(0.5, end - time.monotonic()))

    def _cmd(self, system):
        cmd = [self.exe, '-p', '--output-format', 'json', '--tools', '',
               '--no-session-persistence', '--strict-mcp-config', '--disable-slash-commands']
        if system:
            cmd += ['--system-prompt', system]
        if self.model:
            cmd += ['--model', self.model]
        return cmd + self.extra_args

    def _run_once(self, prompt, system):
        proc = subprocess.Popen(self._cmd(system), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, cwd=self.workdir, env=_clean_env(self.exe),
                                **_popen_kwargs())
        result = {}

        def communicate():
            result['out'], result['err'] = proc.communicate(prompt.encode('utf-8'))

        t = threading.Thread(target=communicate, daemon=True)
        t.start()
        deadline = time.monotonic() + self.timeout
        while t.is_alive():
            t.join(0.5)
            if self.should_stop() or time.monotonic() > deadline:
                proc.kill()
                t.join(5)
                if self.should_stop():
                    raise Aborted()
                raise ClaudeCodeError(_('Timed out ({seconds} s).').format(seconds=self.timeout))

        out = result.get('out', b'').decode('utf-8', 'replace').strip()
        err = result.get('err', b'').decode('utf-8', 'replace').strip()
        try:
            data = json.loads(out)
        except ValueError:
            raise ClaudeCodeError((err or out or _('exit code {code}').format(code=proc.returncode))[:2000])
        text = (data.get('result') or '').strip()
        with self._lock:
            self.cost_usd += float(data.get('total_cost_usd') or 0)
        if data.get('is_error') or proc.returncode != 0 or not text:
            raise ClaudeCodeError((text or err or data.get('subtype') or _('empty response'))[:2000])
        return text

    def generate(self, prompt, system=None):
        for attempt in range(self.max_retries + 1):
            if self.should_stop():
                raise Aborted()
            with self._lock:
                self.calls += 1
            try:
                return self._run_once(prompt, system)
            except ClaudeCodeError as e:
                if NON_RETRYABLE.search(str(e)) or attempt == self.max_retries:
                    raise
                delay = min(300, 15 * 2 ** attempt)
                self.log(_('Claude Code: {error} — retrying in {seconds} s ({attempt}/{max})').format(
                    error=e, seconds=delay, attempt=attempt + 1, max=self.max_retries))
                self._sleep(delay)

    def close(self):
        shutil.rmtree(self.workdir, ignore_errors=True)
