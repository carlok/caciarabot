from caciarabot.normalization import NormalizationOptions, normalize


def test_case_insensitive_default():
    assert normalize("Buongiorno").normalized_text == normalize("BUONGIORNO").normalized_text
    assert normalize("buongiorno").normalized_text == normalize("Buongiorno").normalized_text


def test_apostrophe_variants_normalize_identically():
    ascii_form = normalize("com'è").normalized_text
    typographic_form = normalize("com’è").normalized_text
    assert ascii_form == typographic_form


def test_accents_kept_by_default():
    options = NormalizationOptions()
    assert normalize("però", options).normalized_text != normalize("pero", options).normalized_text


def test_accents_folded_when_enabled():
    options = NormalizationOptions(ignore_accents=True)
    assert normalize("però", options).normalized_text == normalize("pero", options).normalized_text


def test_repeated_letters_kept_by_default():
    options = NormalizationOptions()
    assert normalize("dai", options).normalized_text != normalize("daiiii", options).normalized_text


def test_repeated_letters_collapsed_when_enabled():
    options = NormalizationOptions(collapse_repeated_letters=True)
    assert normalize("daiiii", options).normalized_text == "dai"
    assert (
        normalize("dai", options).normalized_text == normalize("daiiii", options).normalized_text
    )


def test_repeated_letters_collapse_preserves_double_consonants():
    options = NormalizationOptions(collapse_repeated_letters=True)
    # "tutto" legitimately has a doubled "t"; collapsing should leave it as-is.
    assert normalize("tutto", options).normalized_text == "tutto"


def test_original_text_preserved():
    result = normalize("Buongiorno RAGA!!!")
    assert result.original_text == "Buongiorno RAGA!!!"
