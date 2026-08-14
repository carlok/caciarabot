"""Command and passive-message handlers.

All matching/probability/cooldown/filesystem/random logic lives in
engine/ and storage/ — handlers only orchestrate the call sequence and
talk to Telegram, per the clean-interfaces requirement (spec section 43).
"""

from __future__ import annotations

import random

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from caciarabot.engine.ambient import pick_secret_targets, select_emoji_reaction, select_llm_prompt
from caciarabot.engine.decision import select
from caciarabot.engine.matcher import find_matches
from caciarabot.engine.mentions import contains_word, is_bot_cited
from caciarabot.llm import generate_reply
from caciarabot.logging_utils import log_event
from caciarabot.runtime import Runtime
from caciarabot.storage import (
    get_chat_activity,
    get_chat_locale,
    get_chat_members,
    increment_counter,
    is_trigger_on_cooldown,
    record_chat_member,
    record_trigger_fired,
    touch_chat,
)
from caciarabot.telegram.renderer import send_decision, send_emoji_reaction

router = Router(name="caciarabot")

_SECRET_TRIGGER_ID = "llm_secret"


@router.message(Command("help"))
async def cmd_help(message: Message, runtime: Runtime) -> None:
    locale = get_chat_locale(runtime.db, message.chat.id, runtime.bot_config.default_locale)
    await message.answer(runtime.locales.text(locale, "help.text"))


@router.message(Command("status"))
async def cmd_status(message: Message, runtime: Runtime) -> None:
    chat_id = message.chat.id
    locale = get_chat_locale(runtime.db, chat_id, runtime.bot_config.default_locale)
    activity = get_chat_activity(runtime.db, chat_id)
    passive_key = (
        "status.passive_reactions_yes"
        if runtime.bot_config.passive_reactions
        else "status.passive_reactions_no"
    )
    categories = len({rule.category for rule in runtime.rules})

    lines = [
        runtime.locales.text(locale, "status.awake"),
        runtime.locales.text(
            locale, "status.line_passive_reactions", value=runtime.locales.text(locale, passive_key)
        ),
        runtime.locales.text(locale, "status.line_activity", value=round(activity * 100)),
        runtime.locales.text(locale, "status.line_categories", value=categories),
    ]
    await message.answer("\n".join(lines))


@router.message()
async def on_group_message(message: Message, runtime: Runtime, bot: Bot) -> None:
    if message.chat.type not in ("group", "supergroup"):
        return
    if not message.text or message.text.startswith("/"):
        return
    if not runtime.bot_config.passive_reactions:
        return

    chat_id = message.chat.id
    touch_chat(runtime.db, chat_id)
    increment_counter(runtime.db, "global", "messages_observed")

    if message.from_user is not None:
        record_chat_member(runtime.db, chat_id, message.from_user.id, message.from_user.full_name)

    if runtime.bot_config.emoji_reactions_enabled:
        emoji = select_emoji_reaction(
            runtime.bot_config.emoji_reaction_pool, runtime.bot_config.emoji_reaction_probability
        )
        if emoji is not None:
            await send_emoji_reaction(bot, message, emoji)
            increment_counter(runtime.db, "global", "emoji_reactions_sent")
            log_event("emoji_reaction_selected", chat_id=chat_id, emoji=emoji)

    if runtime.bot_config.llm_enabled and runtime.bot_config.llm_cited_reply_enabled and runtime.gemini_api_key:
        replied_to_bot = (
            message.reply_to_message is not None
            and message.reply_to_message.from_user is not None
            and runtime.bot_id is not None
            and message.reply_to_message.from_user.id == runtime.bot_id
        )
        mention_spans = [
            (entity.offset, entity.length)
            for entity in (message.entities or [])
            if entity.type == "mention"
        ]
        if is_bot_cited(
            message.text,
            mention_spans,
            runtime.bot_username,
            replied_to_bot,
            runtime.bot_config.llm_cited_trigger_words,
        ):
            await _handle_cited_reply(message, runtime, replied_to_bot)
            return

    if (
        runtime.bot_config.llm_enabled
        and runtime.bot_config.llm_secret_enabled
        and runtime.gemini_api_key
        and contains_word(message.text, "segreto")
        and not is_trigger_on_cooldown(
            runtime.db, chat_id, _SECRET_TRIGGER_ID, runtime.bot_config.llm_secret_cooldown_seconds
        )
    ):
        prompt = select_llm_prompt(runtime.llm_secret_prompts, runtime.bot_config.llm_secret_probability)
        if prompt is not None:
            record_trigger_fired(runtime.db, chat_id, _SECRET_TRIGGER_ID)
            await _handle_secret(message, runtime, prompt)
            return

    matches = find_matches(message.text, runtime.rules, runtime.normalization_options)
    decisions = []

    if matches:
        increment_counter(runtime.db, "global", "triggers_matched")
        chat_activity = get_chat_activity(runtime.db, chat_id)

        cooldowns_by_rule_id = {rule.id: rule.cooldown_seconds for rule in runtime.rules}

        def is_on_cooldown(trigger_id: str) -> bool:
            cooldown_seconds = cooldowns_by_rule_id.get(trigger_id, 0)
            return is_trigger_on_cooldown(runtime.db, chat_id, trigger_id, cooldown_seconds)

        decisions = select(
            matches=matches,
            chat_activity=chat_activity,
            max_reactions_per_message=runtime.bot_config.max_reactions_per_message,
            is_on_cooldown=is_on_cooldown,
        )

    if decisions:
        for decision in decisions:
            rule = decision.match.rule
            record_trigger_fired(runtime.db, chat_id, rule.id)
            increment_counter(runtime.db, "global", "reactions_sent")
            increment_counter(runtime.db, "trigger", rule.id)
            increment_counter(runtime.db, "category", rule.category)
            log_event(
                "reaction_selected",
                chat_id=chat_id,
                trigger_id=rule.id,
                response_type=decision.response.type,
            )
            await send_decision(message, runtime, decision)
        return

    if matches:
        log_event("reaction_skipped", chat_id=chat_id, decision="none", reason="cooldown_or_probability")

    # LLM reply is independent of trigger matching, but skipped when a
    # trigger already fired above -- one bot-authored message per
    # user message is enough, even though an emoji reaction (not a
    # message) can still land regardless.
    if runtime.bot_config.llm_enabled and runtime.gemini_api_key:
        prompt = select_llm_prompt(runtime.llm_reply_prompts, runtime.bot_config.llm_reply_probability)
        if prompt is not None:
            reply_text = await generate_reply(
                runtime.gemini_api_key, runtime.bot_config.llm_model, prompt, message.text
            )
            if reply_text:
                if runtime.bot_config.llm_dry_run:
                    log_event("llm_reply_dry_run", chat_id=chat_id, text=reply_text)
                else:
                    await message.answer(reply_text)
                increment_counter(runtime.db, "global", "llm_replies_sent")
                log_event("llm_reply_selected", chat_id=chat_id)


async def _handle_cited_reply(message: Message, runtime: Runtime, replied_to_bot: bool) -> None:
    chat_id = message.chat.id
    if not runtime.llm_cited_prompts:
        return

    prompt = random.choice(runtime.llm_cited_prompts)

    if replied_to_bot and message.reply_to_message and message.reply_to_message.text:
        user_message = (
            f'Your earlier message: "{message.reply_to_message.text}"\n'
            f"Reply from the group: {message.text}"
        )
    else:
        user_message = message.text

    reply_text = await generate_reply(
        runtime.gemini_api_key, runtime.bot_config.llm_model, prompt, user_message
    )
    if not reply_text:
        return

    if runtime.bot_config.llm_dry_run:
        log_event("llm_cited_reply_dry_run", chat_id=chat_id, text=reply_text)
    else:
        await message.answer(reply_text)
    increment_counter(runtime.db, "global", "llm_cited_replies_sent")
    log_event("llm_cited_reply_selected", chat_id=chat_id)


async def _handle_secret(message: Message, runtime: Runtime, prompt: str) -> None:
    chat_id = message.chat.id
    members = get_chat_members(runtime.db, chat_id)
    targets = pick_secret_targets(members)
    if not targets:
        log_event("llm_secret_skipped", chat_id=chat_id, reason="no_known_members")
        return

    user_message = "Name(s): " + ", ".join(targets)
    reply_text = await generate_reply(
        runtime.gemini_api_key, runtime.bot_config.llm_model, prompt, user_message
    )
    if not reply_text:
        return

    if runtime.bot_config.llm_dry_run:
        log_event("llm_secret_dry_run", chat_id=chat_id, targets=",".join(targets), text=reply_text)
    else:
        await message.answer(reply_text)
    increment_counter(runtime.db, "global", "llm_secrets_sent")
    log_event("llm_secret_selected", chat_id=chat_id, targets=",".join(targets))
