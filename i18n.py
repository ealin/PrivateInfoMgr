"""
Lightweight i18n module.

Adding a new language:
  1. Create translations/<lang_code>.json with all keys present in zh_TW.json.
  2. Append the code to SUPPORTED_LANGS below.
  The language selector UI updates automatically.
"""

import json
import os
import sys
from typing import Any

from flask import session

# ── Configuration ─────────────────────────────────────────────────────────────

SUPPORTED_LANGS: list[str] = ['zh_TW', 'en']
DEFAULT_LANG:    str        = 'zh_TW'

# ── Internal store ────────────────────────────────────────────────────────────

_translations: dict[str, dict[str, str]] = {}


def _translations_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'translations')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'translations')


def load_translations() -> None:
    """Load all JSON translation files. Call once at app startup."""
    base = _translations_dir()
    for lang in SUPPORTED_LANGS:
        path = os.path.join(base, f'{lang}.json')
        with open(path, 'r', encoding='utf-8') as f:
            _translations[lang] = json.load(f)


# ── Public API ────────────────────────────────────────────────────────────────

def get_locale() -> str:
    """Return the active language code for the current request."""
    try:
        lang = session.get('lang', DEFAULT_LANG)
    except RuntimeError:
        lang = DEFAULT_LANG
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def t(key: str, **kwargs: Any) -> str:
    """
    Look up a translation key in the active language.
    Falls back to DEFAULT_LANG, then to the key itself if not found.
    Supports named placeholders: t('key', name='value').
    """
    lang  = get_locale()
    text  = _translations.get(lang, {}).get(key)
    if text is None:
        text = _translations.get(DEFAULT_LANG, {}).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text


def lang_options() -> list[dict[str, str]]:
    """Return list of {code, label} for all supported languages."""
    return [{'code': c, 'label': _translations.get(c, {}).get(f'lang.{c}', c)}
            for c in SUPPORTED_LANGS]
