"""Typed representations of the parsed configuration and reaction records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from caciarabot.normalization import NormalizationOptions


@dataclass(frozen=True, slots=True)
class BotConfig:
    """Every field has a working default, and every field is overridable
    by a `CACIARABOT_<FIELD_NAME>` environment variable (see config/env.py).
    There is no configuration file: an unset environment means these
    values, which are a usable Italian deployment with the LLM off.
    """

    default_locale: str = "it"
    timezone: str = "Europe/Rome"
    reaction_packs: tuple[str, ...] = ("core-it", "custom")
    max_reactions_per_message: int = 1
    passive_reactions: bool = True
    commands_enabled: bool = True
    emoji_reactions_enabled: bool = False
    emoji_reaction_probability: float = 0.0
    emoji_reaction_pool: tuple[str, ...] = ()
    llm_enabled: bool = False
    llm_model: str = "gemini-3.1-flash-lite"
    llm_dry_run: bool = False
    llm_reply_probability: float = 0.0
    llm_daily_thought_enabled: bool = False
    llm_daily_thought_time: str = "09:00"
    llm_daily_link_probability: float = 0.2
    llm_daily_link_languages: tuple[str, ...] = ("it", "en")
    llm_cited_reply_enabled: bool = False
    llm_cited_trigger_words: tuple[str, ...] = ("caciara",)
    llm_secret_enabled: bool = False
    llm_secret_probability: float = 0.0
    llm_secret_cooldown_seconds: int = 1800
    digest_enabled: bool = False
    digest_time: str = "08:00"
    # reddit is a supported source but not a default -- its public .json
    # endpoints commonly 403 unauthenticated/non-browser requests (see
    # digest/sources.py), so it needs to be opted into explicitly.
    digest_sources: tuple[str, ...] = ("hackernews", "github_trending")
    digest_reddit_subs: tuple[str, ...] = ("programming",)


@dataclass(frozen=True, slots=True)
class LimitsConfig:
    minimum_chat_interval_seconds: int = 0
    maximum_passive_reactions_per_10_minutes: int = 0


@dataclass(frozen=True, slots=True)
class WordMatch:
    values: tuple[str, ...]
    type: Literal["word"] = "word"


@dataclass(frozen=True, slots=True)
class PhraseMatch:
    values: tuple[str, ...]
    type: Literal["phrase"] = "phrase"


Match = WordMatch | PhraseMatch


@dataclass(frozen=True, slots=True)
class TextResponse:
    value: str
    weight: float
    type: Literal["text"] = "text"


@dataclass(frozen=True, slots=True)
class PhotoResponse:
    path: str
    weight: float
    type: Literal["photo"] = "photo"


@dataclass(frozen=True, slots=True)
class RandomPhotoResponse:
    directory: str
    weight: float
    type: Literal["randomPhoto"] = "randomPhoto"


Response = TextResponse | PhotoResponse | RandomPhotoResponse


@dataclass(frozen=True, slots=True)
class ReactionRule:
    id: str
    category: str
    match: Match
    responses: tuple[Response, ...]
    probability: float = 1.0
    cooldown_seconds: int = 0
    priority: int = 0
    normalization_override: NormalizationOptions | None = None
    source_file: str = ""
    source_line: int = 0


def normalization_options_from_dict(data: dict | None) -> NormalizationOptions | None:
    if not data:
        return None
    defaults = NormalizationOptions()
    return NormalizationOptions(
        case_insensitive=data.get("caseInsensitive", defaults.case_insensitive),
        normalize_apostrophes=data.get("normalizeApostrophes", defaults.normalize_apostrophes),
        ignore_accents=data.get("ignoreAccents", defaults.ignore_accents),
        collapse_repeated_letters=data.get(
            "collapseRepeatedLetters", defaults.collapse_repeated_letters
        ),
    )
