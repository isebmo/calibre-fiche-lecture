#!/usr/bin/env python
"""Client minimal pour l'API REST Google Gemini (aucune dépendance externe)."""

import json
import re
import threading
import time
import urllib.error
import urllib.request

try:
    load_translations()
except NameError:  # hors du chargeur d'extensions calibre (cli.py)
    pass

API_BASE = 'https://generativelanguage.googleapis.com/v1beta'
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class GeminiError(Exception):
    pass


class Aborted(Exception):
    pass


def _model_path(model):
    model = model.strip()
    return model if model.startswith('models/') else 'models/' + model


def _http(method, url, api_key, payload=None, timeout=60):
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        'Content-Type': 'application/json',
        'x-goog-api-key': api_key,
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def list_models(api_key, timeout=30):
    """Liste les modèles disponibles qui supportent generateContent."""
    models, token = [], None
    while True:
        url = f'{API_BASE}/models?pageSize=1000' + (f'&pageToken={token}' if token else '')
        try:
            data = _http('GET', url, api_key, timeout=timeout)
        except urllib.error.HTTPError as e:
            raise GeminiError(_error_message(e)) from e
        for m in data.get('models', []):
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                models.append(m['name'].removeprefix('models/'))
        token = data.get('nextPageToken')
        if not token:
            return models


def _error_message(http_error):
    try:
        body = json.loads(http_error.read().decode('utf-8'))
        return f"HTTP {http_error.code} : {body['error'].get('message', body)}"
    except Exception:
        return f'HTTP {http_error.code} : {http_error.reason}'


class GeminiClient:

    def __init__(self, api_key, model, temperature=0.4, max_retries=6, min_interval=0.0,
                 timeout=300, should_stop=None, log=None):
        if not api_key:
            raise GeminiError(_('No Gemini API key is configured.'))
        self.api_key = api_key
        self.url = f'{API_BASE}/{_model_path(model)}:generateContent'
        self.temperature = temperature
        self.max_retries = max_retries
        self.min_interval = min_interval
        self.timeout = timeout
        self.should_stop = should_stop or (lambda: False)
        self.log = log or (lambda *a: None)
        self._lock = threading.Lock()
        self._next_slot = 0.0
        self.calls = 0
        self.label = f'Gemini ({model})'
        self.cache_tag = f'gemini:{model}'

    def close(self):
        pass

    def _sleep(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if self.should_stop():
                raise Aborted()
            time.sleep(min(0.5, end - time.monotonic()))

    def _wait_rate_limit(self):
        # Réserve un créneau, partagé entre threads, espacé de min_interval.
        with self._lock:
            now = time.monotonic()
            slot = max(now, self._next_slot)
            self._next_slot = slot + self.min_interval
        if slot > now:
            self._sleep(slot - now)

    def generate(self, prompt, system=None):
        payload = {
            'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
            'generationConfig': {'temperature': self.temperature},
        }
        if system:
            payload['systemInstruction'] = {'parts': [{'text': system}]}

        for attempt in range(self.max_retries + 1):
            if self.should_stop():
                raise Aborted()
            self._wait_rate_limit()
            try:
                self.calls += 1
                data = _http('POST', self.url, self.api_key, payload, timeout=self.timeout)
                return self._parse(data)
            except urllib.error.HTTPError as e:
                msg = _error_message(e)
                if e.code not in RETRYABLE_STATUS or attempt == self.max_retries:
                    raise GeminiError(msg) from e
                delay = self._retry_delay(e, msg, attempt)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if attempt == self.max_retries:
                    raise GeminiError(_('Network error: {error}').format(error=e)) from e
                msg, delay = _('Network error: {error}').format(error=e), min(120, 5 * 2 ** attempt)
            self.log(_('{message} — retrying in {seconds:.0f} s ({attempt}/{max})').format(
                message=msg, seconds=delay, attempt=attempt + 1, max=self.max_retries))
            self._sleep(delay)

    @staticmethod
    def _retry_delay(err, msg, attempt):
        ra = err.headers.get('Retry-After') if err.headers else None
        if ra and ra.isdigit():
            return float(ra) + 1
        m = re.search(r'retry in ([\d.]+)s', msg, re.I) or re.search(r'"retryDelay":\s*"([\d.]+)s"', msg)
        if m:
            return float(m.group(1)) + 1
        return min(120, 5 * 2 ** attempt)

    @staticmethod
    def _parse(data):
        candidates = data.get('candidates') or []
        if not candidates:
            reason = (data.get('promptFeedback') or {}).get('blockReason', _('empty response'))
            raise GeminiError(_('Request refused by Gemini ({reason}).').format(reason=reason))
        cand = candidates[0]
        parts = (cand.get('content') or {}).get('parts') or []
        text = ''.join(p.get('text', '') for p in parts if not p.get('thought')).strip()
        finish = cand.get('finishReason', '')
        if not text:
            raise GeminiError(_('Empty response from Gemini (finishReason={reason}).').format(reason=finish))
        if finish == 'MAX_TOKENS':
            text += '\n\n*(' + _('Truncated response: length limit reached.') + ')*'
        return text
