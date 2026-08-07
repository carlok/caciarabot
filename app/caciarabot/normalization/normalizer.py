"""Italian-oriented text normalization.

Real Italian group-chat text is informal: missing accents, mixed
apostrophe glyphs, and stretched-out letters ("daiiii"). This module
turns a raw message into a normalized form the matching engine can
compare triggers against, while always keeping the original text
alongside it.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# U+2019 RIGHT SINGLE QUOTATION MARK, U+2018 LEFT SINGLE QUOTATION MARK,
# U+02BC MODIFIER LETTER APOSTROPHE — all used informally as apostrophes
# in Italian chat text ("com'è" / "com’è").
_APOSTROPHE_VARIANTS = "’‘ʼ`´"
_APOSTROPHE_TRANSLATION = {ord(ch): "'" for ch in _APOSTROPHE_VARIANTS}

_REPEATED_CHAR_PATTERN = re.compile(r"(.)\1{2,}", re.UNICODE)


@dataclass(frozen=True, slots=True)
class NormalizationOptions:
    """Configurable normalization behavior (global default, overridable per rule)."""

    case_insensitive: bool = True
    normalize_apostrophes: bool = True
    ignore_accents: bool = False
    collapse_repeated_letters: bool = False

    def merged_with(self, override: "NormalizationOptions | None") -> "NormalizationOptions":
        """Per-rule overrides win over these (global) values, field by field."""
        if override is None:
            return self
        return NormalizationOptions(
            case_insensitive=override.case_insensitive,
            normalize_apostrophes=override.normalize_apostrophes,
            ignore_accents=override.ignore_accents,
            collapse_repeated_letters=override.collapse_repeated_letters,
        )


@dataclass(frozen=True, slots=True)
class NormalizedText:
    original_text: str
    normalized_text: str


def _fold_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", without_marks)


def _collapse_repeated_letters(text: str) -> str:
    # Only collapse runs of 3+ (the regex already requires that) down to a
    # single character. Genuine Italian double consonants ("tutto",
    # "ragazzi") have runs of exactly 2 and are left untouched.
    return _REPEATED_CHAR_PATTERN.sub(lambda m: m.group(1), text)


def normalize(text: str, options: NormalizationOptions = NormalizationOptions()) -> NormalizedText:
    normalized = unicodedata.normalize("NFC", text)

    if options.normalize_apostrophes:
        normalized = normalized.translate(_APOSTROPHE_TRANSLATION)

    if options.case_insensitive:
        normalized = normalized.casefold()

    if options.ignore_accents:
        normalized = _fold_accents(normalized)

    if options.collapse_repeated_letters:
        normalized = _collapse_repeated_letters(normalized)

    return NormalizedText(original_text=text, normalized_text=normalized)
