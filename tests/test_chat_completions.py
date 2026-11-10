import asyncio
import logging

from aiohttp import web
from aiohttp.test_utils import TestServer
from caciarabot.llm.chat_completions import generate_reply


def _serve(handler):
    """Run `handler` as POST /v1/chat/completions; returns (server, seen)."""
    seen: list[dict] = []

    async def wrapped(request: web.Request) -> web.Response:
        seen.append(
            {
                "path": request.path,
                "authorization": request.headers.get("Authorization"),
                "body": await request.json(),
            }
        )
        return await handler(request)

    app = web.Application()
    app.router.add_post("/v1/chat/completions", wrapped)
    return TestServer(app), seen


def _call(server: TestServer, **kwargs):
    async def run():
        await server.start_server()
        try:
            return await generate_reply(
                "secret-key",
                "some-model",
                "SYSTEM PROMPT",
                "user text",
                base_url=str(server.make_url("/v1")),
                **kwargs,
            )
        finally:
            await server.close()

    return asyncio.run(run())


def _completion(content, finish_reason="stop"):
    return web.json_response(
        {"choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": finish_reason}]}
    )


def test_sends_openai_chat_completions_request_and_returns_stripped_text():
    async def handler(_request):
        return _completion("  ciao mondo \n")

    server, seen = _serve(handler)

    assert _call(server) == "ciao mondo"
    assert seen[0]["path"] == "/v1/chat/completions"
    assert seen[0]["authorization"] == "Bearer secret-key"
    body = seen[0]["body"]
    assert body["model"] == "some-model"
    assert body["messages"] == [
        {"role": "system", "content": "SYSTEM PROMPT"},
        {"role": "user", "content": "user text"},
    ]
    assert body["max_tokens"] == 400


def test_trailing_slash_on_base_url_is_harmless():
    async def handler(_request):
        return _completion("ok")

    server, seen = _serve(handler)

    async def run():
        await server.start_server()
        try:
            return await generate_reply(
                "k", "m", "s", "u", base_url=str(server.make_url("/v1")) + "/"
            )
        finally:
            await server.close()

    assert asyncio.run(run()) == "ok"
    assert seen[0]["path"] == "/v1/chat/completions"


def test_reply_cut_off_by_the_token_limit_is_discarded(caplog):
    async def handler(_request):
        return _completion("half a sent", finish_reason="length")

    server, _ = _serve(handler)

    with caplog.at_level(logging.INFO, logger="caciarabot"):
        assert _call(server) is None
    assert "response cut off at max_tokens" in caplog.text


def test_http_error_returns_none_and_logs_status(caplog):
    async def handler(_request):
        return web.Response(status=429, text="RESOURCE_EXHAUSTED")

    server, _ = _serve(handler)

    with caplog.at_level(logging.INFO, logger="caciarabot"):
        assert _call(server) is None
    assert "status=429" in caplog.text


def test_redirect_is_not_followed():
    followed: list[str] = []

    async def redirect(_request):
        raise web.HTTPFound("/v1/elsewhere")

    async def elsewhere(request):
        followed.append(request.headers.get("Authorization", ""))
        return _completion("should never be read")

    app = web.Application()
    app.router.add_post("/v1/chat/completions", redirect)
    app.router.add_get("/v1/elsewhere", elsewhere)
    app.router.add_post("/v1/elsewhere", elsewhere)

    assert _call(TestServer(app)) is None
    assert followed == []


def test_malformed_or_empty_bodies_return_none():
    for payload in (
        {"choices": []},
        {"error": "nope"},
        {"choices": [{"message": {"content": None}, "finish_reason": "stop"}]},
        {"choices": [{"message": {"content": "   "}, "finish_reason": "stop"}]},
    ):

        async def handler(_request, payload=payload):
            return web.json_response(payload)

        server, _ = _serve(handler)
        assert _call(server) is None, payload


def test_unreachable_server_returns_none():
    async def run():
        return await generate_reply("k", "m", "s", "u", base_url="http://127.0.0.1:1/v1")

    assert asyncio.run(run()) is None
