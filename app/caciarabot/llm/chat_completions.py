"""Minimal client for any OpenAI-compatible chat-completions endpoint.

The bot only ever needs one thing from a model: a system prompt and one
user message in, a short piece of text out. That is the lowest common
denominator of every provider, so the wire format is the OpenAI
`/chat/completions` one. Gemini, OpenAI, OpenRouter, Ollama and
Anthropic's compatibility layer all accept it, which makes moving between
them a matter of `CACIARABOT_LLM_BASE_URL`, a key and a model name.

Deliberately not an SDK: this bot makes a handful of calls a day, so a
single `aiohttp` POST (aiohttp is already a dependency via aiogram) covers
it without adding a package for something this small.
"""

from __future__ import annotations

import aiohttp

from caciarabot.logging_utils import log_event

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
_REQUEST_TIMEOUT_SECONDS = 15
_MAX_OUTPUT_TOKENS = 400


async def generate_reply(
    api_key: str,
    model: str,
    system_prompt: str,
    user_message: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
) -> str | None:
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": _MAX_OUTPUT_TOKENS,
        "temperature": 1.0,
    }
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        timeout = aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # No redirects: a chat-completions endpoint never legitimately
            # sends one, and following it would carry the key along.
            async with session.post(
                url, json=payload, headers=headers, allow_redirects=False
            ) as response:
                if response.status != 200:
                    body = await response.text()
                    log_event("llm_call_failed", status=response.status, body=body[:200])
                    return None
                data = await response.json()
    except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
        log_event("llm_call_failed", reason=str(exc))
        return None

    try:
        choice = data["choices"][0]
        content = choice["message"]["content"]
    except (KeyError, IndexError, TypeError):
        log_event("llm_call_failed", reason="no choices in response")
        return None

    if choice.get("finish_reason") == "length":
        log_event("llm_call_failed", reason="response cut off at max_tokens")
        return None

    if not isinstance(content, str):
        return None
    return content.strip() or None
