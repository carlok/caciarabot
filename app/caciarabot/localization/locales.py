"""Loads locales/*.json and resolves user-facing strings by key."""

from __future__ import annotations

import json
from pathlib import Path


class Locales:
    def __init__(self, translations: dict[str, dict[str, str]], default_locale: str):
        self._translations = translations
        self._default_locale = default_locale

    def text(self, locale: str, key: str, **params: object) -> str:
        strings = self._translations.get(locale) or self._translations[self._default_locale]
        template = strings.get(key)
        if template is None:
            fallback = self._translations[self._default_locale].get(key)
            if fallback is None:
                return key
            template = fallback
        return template.format(**params) if params else template


def load_locales(locales_dir: Path, default_locale: str) -> Locales:
    translations: dict[str, dict[str, str]] = {}
    for locale_file in sorted(locales_dir.glob("*.json")):
        locale_code = locale_file.stem
        translations[locale_code] = json.loads(locale_file.read_text(encoding="utf-8"))
    return Locales(translations, default_locale)
