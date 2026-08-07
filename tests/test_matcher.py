from caciarabot.config.models import PhraseMatch, ReactionRule, TextResponse, WordMatch
from caciarabot.engine.matcher import find_matches
from caciarabot.normalization import NormalizationOptions


def _rule(rule_id: str, match, normalization_override=None) -> ReactionRule:
    return ReactionRule(
        id=rule_id,
        category="test",
        match=match,
        responses=(TextResponse(value="ok", weight=1),),
        normalization_override=normalization_override,
    )


def test_word_match_matches_whole_word():
    rule = _rule("roma", WordMatch(values=("roma",)))
    results = find_matches("Roma oggi è calda", [rule], NormalizationOptions())
    assert len(results) == 1
    assert results[0].rule.id == "roma"


def test_word_match_does_not_match_inside_larger_word():
    rule = _rule("roma", WordMatch(values=("roma",)))
    results = find_matches("l'aroma del caffè", [rule], NormalizationOptions())
    assert results == []


def test_word_match_is_case_insensitive_by_default():
    rule = _rule("buongiorno", WordMatch(values=("buongiorno",)))
    for text in ("buongiorno", "Buongiorno", "BUONGIORNO"):
        results = find_matches(text, [rule], NormalizationOptions())
        assert len(results) == 1, text


def test_phrase_match():
    rule = _rule("buongiorno_a_tutti", PhraseMatch(values=("buongiorno a tutti",)))
    assert find_matches("Ragazzi, buongiorno a tutti!", [rule], NormalizationOptions())
    assert find_matches("buongiorno a voi", [rule], NormalizationOptions()) == []


def test_emoji_word_match():
    rule = _rule("clown", WordMatch(values=("🤡",)))
    results = find_matches("ma dai 🤡", [rule], NormalizationOptions())
    assert len(results) == 1


def test_per_rule_accent_override_beats_global_default():
    global_options = NormalizationOptions(ignore_accents=False)
    rule = _rule(
        "vabbe",
        WordMatch(values=("vabbè",)),
        normalization_override=NormalizationOptions(ignore_accents=True),
    )
    results = find_matches("vabbe dai", [rule], global_options)
    assert len(results) == 1


def test_multiple_rules_can_each_match_independently():
    rules = [
        _rule("buongiorno", WordMatch(values=("buongiorno",))),
        _rule("disastro", WordMatch(values=("disastro",))),
    ]
    results = find_matches("Buongiorno ragazzi, che disastro", rules, NormalizationOptions())
    matched_ids = {r.rule.id for r in results}
    assert matched_ids == {"buongiorno", "disastro"}
