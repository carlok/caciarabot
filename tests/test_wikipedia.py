from caciarabot.llm.wikipedia import _parse_summary, looks_technical


def _summary(extract: str, title: str = "Chiesa dell'Immacolata", url: str | None = "https://it.wikipedia.org/wiki/X"):
    data = {"title": title, "extract": extract}
    if url is not None:
        data["content_urls"] = {"desktop": {"page": url}}
    return data


def test_parses_a_well_formed_summary():
    extract = "La chiesa dell'Immacolata si trova a Piombino. " * 5
    article = _parse_summary(_summary(extract), "it")

    assert article is not None
    assert article.title == "Chiesa dell'Immacolata"
    assert article.url == "https://it.wikipedia.org/wiki/X"
    assert article.language == "it"
    assert article.extract == extract.strip()


def test_rejects_short_stub_extract():
    # English Wikipedia serves many one-line stubs with nothing to react to
    assert _parse_summary(_summary("PLEKHA8 is a protein-coding gene."), "en") is None


def test_rejects_missing_title():
    extract = "Un testo abbastanza lungo per superare la soglia minima. " * 5
    assert _parse_summary(_summary(extract, title=None), "it") is None


def test_rejects_missing_url():
    extract = "Un testo abbastanza lungo per superare la soglia minima. " * 5
    assert _parse_summary(_summary(extract, url=None), "it") is None


def test_rejects_empty_response():
    assert _parse_summary({}, "it") is None


def test_rejects_whitespace_only_extract():
    assert _parse_summary(_summary("   \n  "), "it") is None


def test_looks_technical_matches_software_topics():
    extract = "A programming language used for systems software. " * 5
    assert looks_technical("Python (programming language)", extract)


def test_looks_technical_rejects_plain_literature():
    extract = "A novel by Umberto Eco set in a medieval monastery. " * 5
    assert not looks_technical("Il nome della rosa", extract)
