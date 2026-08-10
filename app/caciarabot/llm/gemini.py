"""Minimal Gemini REST client.

Deliberately not the official `google-generativeai` SDK: this bot makes
at most a couple of calls a day, so a single `aiohttp` POST (aiohttp is
already a transitive dependency via aiogram) covers it without adding
a new dependency for something this small.
"""

from __future__ import annotations

import aiohttp

from caciarabot.logging_utils import log_event

_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_REQUEST_TIMEOUT_SECONDS = 15


async def generate_reply(
    api_key: str, model: str, system_prompt: str, user_message: str
) -> str | None:
    url = f"{_API_BASE}/{model}:generateContent"
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_message}]}],
        "generationConfig": {"maxOutputTokens": 400, "temperature": 1.0},
    }

    try:
        timeout = aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                url, params={"key": api_key}, json=payload
            ) as response:
                if response.status != 200:
                    body = await response.text()
                    log_event("llm_call_failed", status=response.status, body=body[:200])
                    return None
                data = await response.json()
    except (aiohttp.ClientError, TimeoutError) as exc:
        log_event("llm_call_failed", reason=str(exc))
        return None

    try:
        candidate = data["candidates"][0]
        # A response can legitimately split its output across multiple
        # `parts` entries -- reading only parts[0] silently drops the
        # rest and looks exactly like a mid-sentence truncation bug.
        text = "".join(part.get("text", "") for part in candidate["content"]["parts"])
    except (KeyError, IndexError):
        log_event("llm_call_failed", reason="no candidates in response")
        return None

    if candidate.get("finishReason") == "MAX_TOKENS":
        log_event("llm_call_failed", reason="response cut off at maxOutputTokens")
        return None

    return text.strip() or None
