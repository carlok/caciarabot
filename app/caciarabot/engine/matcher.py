"""Word and phrase trigger matching against a normalized message.

Each rule may override the global normalization options (e.g. a rule
might want accent folding while the global default keeps accents), so
matching re-normalizes the message per-rule rather than relying on a
single normalized form for every comparison.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from caciarabot.config.models import Match, PhraseMatch, ReactionRule, WordMatch
from caciarabot.normalization import NormalizationOptions, normalize


@dataclass(frozen=True, slots=True)
class MatchResult:
    rule: ReactionRule
    matched_value: str


def _boundary_pattern(value: str) -> re.Pattern[str]:
    # Plain \b relies on \w on both sides of the boundary, which breaks for
    # values that start/end with a non-word character (e.g. an emoji) —
    # there's no boundary between two non-word characters. Only require a
    # word-boundary lookaround on the edges that are actually word chars.
    escaped = re.escape(value)
    prefix = r"(?<!\w)" if value[:1].isalnum() else ""
    suffix = r"(?!\w)" if value[-1:].isalnum() else ""
    return re.compile(prefix + escaped + suffix, re.UNICODE)


def _matches(match: Match, normalized_message: str, normalized_values: list[str]) -> str | None:
    for value in normalized_values:
        if not value:
            continue
        if _boundary_pattern(value).search(normalized_message):
            return value
    return None


def find_matches(
    original_text: str,
    rules: list[ReactionRule],
    global_options: NormalizationOptions,
) -> list[MatchResult]:
    results: list[MatchResult] = []

    for rule in rules:
        effective_options = global_options.merged_with(rule.normalization_override)
        normalized_message = normalize(original_text, effective_options).normalized_text
        normalized_values = [
            normalize(value, effective_options).normalized_text for value in rule.match.values
        ]

        if isinstance(rule.match, (WordMatch, PhraseMatch)):
            matched_value = _matches(rule.match, normalized_message, normalized_values)
            if matched_value is not None:
                results.append(MatchResult(rule=rule, matched_value=matched_value))

    return results
