from caciarabot.engine.mentions import is_bot_cited, is_bot_mentioned


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
