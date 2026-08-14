from caciarabot.digest.sources import _parse_github_trending, _parse_hackernews, _parse_reddit


def test_parse_hackernews_uses_story_url_when_present():
    data = {
        "hits": [
            {"title": "Something neat", "url": "https://example.com/post", "objectID": "123", "story_text": None}
        ]
    }
    candidates = _parse_hackernews(data)
    assert len(candidates) == 1
    assert candidates[0].source == "hackernews"
    assert candidates[0].title == "Something neat"
    assert candidates[0].url == "https://example.com/post"
    assert candidates[0].excerpt == ""


def test_parse_hackernews_falls_back_to_discussion_link_for_text_posts():
    data = {"hits": [{"title": "Ask HN: thing", "url": None, "objectID": "456", "story_text": "body text"}]}
    candidates = _parse_hackernews(data)
    assert candidates[0].url == "https://news.ycombinator.com/item?id=456"
    assert candidates[0].excerpt == "body text"


def test_parse_hackernews_skips_hits_missing_title_or_id():
    data = {"hits": [{"title": None, "url": "https://x.com", "objectID": "1"}, {"title": "ok", "objectID": None}]}
    assert _parse_hackernews(data) == []


def test_parse_hackernews_empty_response_returns_empty_list():
    assert _parse_hackernews({}) == []


def test_parse_github_trending():
    data = {
        "items": [
            {
                "full_name": "someone/repo",
                "html_url": "https://github.com/someone/repo",
                "description": "a neat repo",
                "stargazers_count": 500,
            }
        ]
    }
    candidates = _parse_github_trending(data)
    assert len(candidates) == 1
    assert candidates[0].source == "github_trending"
    assert candidates[0].title == "someone/repo"
    assert candidates[0].url == "https://github.com/someone/repo"
    assert candidates[0].excerpt == "a neat repo"


def test_parse_github_trending_skips_items_missing_fields():
    data = {"items": [{"full_name": None, "html_url": "https://x.com"}]}
    assert _parse_github_trending(data) == []


def test_parse_github_trending_malformed_response_returns_empty_list():
    assert _parse_github_trending({}) == []


def test_parse_reddit_link_post():
    data = {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "cool link",
                        "url": "https://external.example/article",
                        "permalink": "/r/programming/comments/abc/cool_link/",
                        "is_self": False,
                        "selftext": "",
                    }
                }
            ]
        }
    }
    candidates = _parse_reddit(data)
    assert len(candidates) == 1
    assert candidates[0].source == "reddit"
    assert candidates[0].url == "https://external.example/article"


def test_parse_reddit_self_post_uses_permalink():
    data = {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "discussion",
                        "url": "https://www.reddit.com/r/programming/comments/xyz/discussion/",
                        "permalink": "/r/programming/comments/xyz/discussion/",
                        "is_self": True,
                        "selftext": "some body text",
                    }
                }
            ]
        }
    }
    candidates = _parse_reddit(data)
    assert candidates[0].url == "https://www.reddit.com/r/programming/comments/xyz/discussion/"
    assert candidates[0].excerpt == "some body text"


def test_parse_reddit_skips_posts_missing_title_or_permalink():
    data = {"data": {"children": [{"data": {"title": None, "permalink": "/r/x/1/"}}]}}
    assert _parse_reddit(data) == []


def test_parse_reddit_malformed_response_returns_empty_list():
    assert _parse_reddit({}) == []
