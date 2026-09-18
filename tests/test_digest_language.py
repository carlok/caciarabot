"""Language filtering for the digest, all offline.

The live behaviour these encode was checked against the real web once:
github.com serves lang="en" even for a Chinese README (hence the raw
README fetch), and Wikipedia answers 403 without a User-Agent.
"""

from caciarabot.digest.language import judge_document, looks_non_english, readme_url

_CHINESE_DESCRIPTION = "大模型（LLM）全栈学习路线与中文教程🔥：覆盖 Prompt Engineering、RAG、AI Agent"
_ENGLISH_DESCRIPTION = "A Swift library for reading, writing, and manipulating Xcode's project files"


def test_non_latin_description_is_rejected():
    assert looks_non_english(_CHINESE_DESCRIPTION) is True
    assert looks_non_english("Руководство по установке") is True


def test_english_description_is_kept():
    assert looks_non_english(_ENGLISH_DESCRIPTION) is False


def test_emoji_and_punctuation_do_not_trip_the_ratio():
    assert looks_non_english("🍊☁️ Open-source* apps that replace a SaaS product") is False


def test_greek_letters_read_as_mathematics_not_as_greek():
    """A lone alpha in a title is far more often maths than Greek prose."""
    assert looks_non_english("α-β pruning explained") is False


def test_latin_script_other_languages_pass_the_metadata_stage():
    """By design: ten words of French can't be told from English reliably.

    The page check settles these, so the cheap stage stays high-precision.
    """
    assert looks_non_english("Le Monde diplomatique") is False


def test_empty_text_is_not_rejected():
    assert looks_non_english("") is False
    assert looks_non_english("12345 !!! ---") is False


def test_declared_html_lang_wins():
    assert judge_document('<html lang="en"><body>ciao</body></html>') is True
    assert judge_document('<html lang="it"><body>hello</body></html>') is False
    assert judge_document("<html LANG='en-GB'><body>x</body></html>") is True


def test_undeclared_english_prose_is_accepted():
    body = "<html><body>" + ("the quick brown fox is in the garden and it has a hat " * 30) + "</body></html>"
    assert judge_document(body) is True


def test_undeclared_non_latin_body_is_rejected():
    assert judge_document("<html><body>" + "大模型全栈学习路线与中文教程 " * 40 + "</body></html>") is False


def test_too_little_text_is_undetermined_rather_than_rejected():
    assert judge_document("<html><body>hello there</body></html>") is None


def test_scripts_and_styles_do_not_count_as_prose():
    body = "<html><body><script>" + ("var a = 1; " * 200) + "</script>hi</body></html>"
    assert judge_document(body) is None


def test_github_repo_maps_to_its_raw_readme():
    assert (
        readme_url("https://github.com/apple/xcode-project-format")
        == "https://raw.githubusercontent.com/apple/xcode-project-format/HEAD/README.md"
    )


def test_github_trailing_slash_and_query_are_tolerated():
    assert readme_url("https://github.com/a/b/?tab=readme#x") == (
        "https://raw.githubusercontent.com/a/b/HEAD/README.md"
    )


def test_github_non_repo_paths_are_not_readmes():
    assert readme_url("https://github.com/topics/ai") is None
    assert readme_url("https://github.com/asciimoo/hister/issues/4") is None


def test_non_github_url_has_no_readme():
    assert readme_url("https://en.wikipedia.org/wiki/Wax_motor") is None
