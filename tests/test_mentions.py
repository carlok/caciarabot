from caciarabot.engine.mentions import contains_word, is_bot_cited, is_bot_mentioned


def test_mention_detected_via_entity_span():
    text = "ehi @caciara_bot che dici"
    # "@caciara_bot" starts at index 4, length 12
    spans = [(4, 12)]
    assert is_bot_mentioned(text, spans, "caciara_bot")


def test_mention_is_case_insensitive():
    text = "EHI @Caciara_Bot rispondi"
    spans = [(4, 12)]
    assert is_bot_mentioned(text, spans, "caciara_bot")


def test_no_mention_entity_means_no_mention():
    text = "parliamo di windows oggi"
    assert not is_bot_mentioned(text, [], "caciara_bot")


def test_mention_of_a_different_user_does_not_match():
    text = "ehi @altro_bot che dici"
    spans = [(4, 10)]
    assert not is_bot_mentioned(text, spans, "caciara_bot")


def test_cited_via_reply_to_bot_regardless_of_text():
    assert is_bot_cited("qualsiasi cosa", [], "caciara_bot", replied_to_bot=True)


def test_cited_via_mention_when_not_a_reply():
    text = "@caciara_bot ciao"
    spans = [(0, 12)]
    assert is_bot_cited(text, spans, "caciara_bot", replied_to_bot=False)


def test_not_cited_without_mention_or_reply():
    assert not is_bot_cited("solo una frase normale", [], "caciara_bot", replied_to_bot=False)


def test_not_cited_when_bot_username_unknown():
    text = "@caciara_bot ciao"
    spans = [(0, 12)]
    assert not is_bot_cited(text, spans, None, replied_to_bot=False)


def test_contains_word_matches_case_insensitively():
    assert contains_word("che CACIARA oggi", "caciara")


def test_contains_word_respects_boundaries():
    # "caciara" inside "caciarabot" (no separator) is not a standalone word
    assert not contains_word("scrivi a caciarabot", "caciara")


def test_contains_word_no_match():
    assert not contains_word("tutto tranquillo", "caciara")


def test_cited_via_extra_trigger_word():
    assert is_bot_cited(
        "che caciara oggi",
        [],
        "caciara_bot",
        replied_to_bot=False,
        extra_trigger_words=("caciara",),
    )


def test_not_cited_via_trigger_word_when_not_configured():
    assert not is_bot_cited(
        "che caciara oggi", [], "caciara_bot", replied_to_bot=False, extra_trigger_words=()
    )


def test_trigger_word_does_not_match_inside_larger_word():
    assert not is_bot_cited(
        "scrivi a caciarabot",
        [],
        "caciara_bot",
        replied_to_bot=False,
        extra_trigger_words=("caciara",),
    )
