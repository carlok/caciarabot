"""Command and passive-message handlers.

All matching/probability/cooldown/filesystem/random logic lives in
engine/ and storage/ — handlers only orchestrate the call sequence and
talk to Telegram, per the clean-interfaces requirement (spec section 43).
"""

from __future__ import annotations

import random
from pathlib import Path

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from caciarabot.bootstrap import load_configuration, load_prompt_pools
from caciarabot.engine.ambient import pick_secret_targets, select_emoji_reaction, select_llm_prompt
from caciarabot.engine.decision import select
from caciarabot.engine.matcher import find_matches
from caciarabot.engine.mentions import contains_word, is_bot_cited
from caciarabot.llm import generate_reply
from caciarabot.localization import load_locales
from caciarabot.logging_utils import log_event
from caciarabot.runtime import Runtime
from caciarabot.storage import (
    disable_category,
    enable_category,
    get_chat_activity,
    get_chat_locale,
    get_chat_members,
    get_counter,
    get_disabled_categories,
    get_top_counters,
    increment_counter,
    is_chat_awake,
    is_trigger_on_cooldown,
    record_chat_member,
    record_trigger_fired,
    set_chat_awake,
    touch_chat,
)
from caciarabot.telegram.permissions import is_authorized
from caciarabot.telegram.renderer import send_decision, send_emoji_reaction

router = Router(name="caciarabot")

_SECRET_TRIGGER_ID = "llm_secret"


async def _require_admin(message: Message, runtime: Runtime, bot: Bot, locale: str) -> bool:
    if message.from_user is None or not await is_authorized(
        bot.get_chat_member, message.chat.id, message.from_user.id, runtime.owner_id
    ):
        await message.answer(runtime.locales.text(locale, "permission.denied"))
        return False
    return True


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
    all_categories = {rule.category for rule in runtime.rules}
    disabled = get_disabled_categories(runtime.db, chat_id)
    categories = len(all_categories - disabled)
    awake_key = "status.awake" if is_chat_awake(runtime.db, chat_id) else "status.sleeping"

    lines = [
        runtime.locales.text(locale, awake_key),
        runtime.locales.text(
            locale, "status.line_passive_reactions", value=runtime.locales.text(locale, passive_key)
        ),
        runtime.locales.text(locale, "status.line_activity", value=round(activity * 100)),
        runtime.locales.text(locale, "status.line_categories", value=categories),
    ]
    await message.answer("\n".join(lines))


@router.message(Command("sleep"))
async def cmd_sleep(message: Message, runtime: Runtime, bot: Bot) -> None:
    chat_id = message.chat.id
    locale = get_chat_locale(runtime.db, chat_id, runtime.bot_config.default_locale)
    if not await _require_admin(message, runtime, bot, locale):
        return
    set_chat_awake(runtime.db, chat_id, False)
    await message.answer(runtime.locales.text(locale, "status.sleeping"))


@router.message(Command("wake"))
async def cmd_wake(message: Message, runtime: Runtime, bot: Bot) -> None:
    chat_id = message.chat.id
    locale = get_chat_locale(runtime.db, chat_id, runtime.bot_config.default_locale)
    if not await _require_admin(message, runtime, bot, locale):
        return
    set_chat_awake(runtime.db, chat_id, True)
    await message.answer(runtime.locales.text(locale, "status.awake"))


@router.message(Command("categories"))
async def cmd_categories(
    message: Message, runtime: Runtime, bot: Bot, command: CommandObject
) -> None:
    chat_id = message.chat.id
    locale = get_chat_locale(runtime.db, chat_id, runtime.bot_config.default_locale)
    all_categories = sorted({rule.category for rule in runtime.rules})
    parts = (command.args or "").split(maxsplit=1)

    if len(parts) == 2 and parts[0] in ("enable", "disable"):
        if not await _require_admin(message, runtime, bot, locale):
            return

        action, category_name = parts[0], parts[1].strip()
        if category_name not in all_categories:
            await message.answer(
                runtime.locales.text(locale, "categories.unknown", category=category_name)
            )
            return

        if action == "enable":
            enable_category(runtime.db, chat_id, category_name)
            await message.answer(
                runtime.locales.text(locale, "categories.enabled_confirm", category=category_name)
            )
        else:
            disable_category(runtime.db, chat_id, category_name)
            await message.answer(
                runtime.locales.text(locale, "categories.disabled_confirm", category=category_name)
            )
        return

    disabled = get_disabled_categories(runtime.db, chat_id)
    lines = [runtime.locales.text(locale, "categories.list_header")]
    for category in all_categories:
        state_key = (
            "categories.status_disabled" if category in disabled else "categories.status_enabled"
        )
        lines.append(f"- {category}: {runtime.locales.text(locale, state_key)}")
    await message.answer("\n".join(lines))


@router.message(Command("stats"))
async def cmd_stats(message: Message, runtime: Runtime) -> None:
    chat_id = message.chat.id
    locale = get_chat_locale(runtime.db, chat_id, runtime.bot_config.default_locale)

    lines = [
        runtime.locales.text(
            locale, "stats.line_messages", value=get_counter(runtime.db, "global", "messages_observed")
        ),
        runtime.locales.text(
            locale, "stats.line_triggers", value=get_counter(runtime.db, "global", "triggers_matched")
        ),
        runtime.locales.text(
            locale, "stats.line_reactions", value=get_counter(runtime.db, "global", "reactions_sent")
        ),
    ]

    top_triggers = get_top_counters(runtime.db, "trigger", 3)
    if top_triggers:
        lines.append("")
        lines.append(runtime.locales.text(locale, "stats.top_header"))
        for i, row in enumerate(top_triggers, start=1):
            lines.append(f"{i}. {row['key']} — {row['count']}")

    await message.answer("\n".join(lines))


@router.message(Command("reload"))
async def cmd_reload(message: Message, runtime: Runtime, bot: Bot) -> None:
    chat_id = message.chat.id
    locale = get_chat_locale(runtime.db, chat_id, runtime.bot_config.default_locale)
    if not await _require_admin(message, runtime, bot, locale):
        return

    bot_config, normalization_options, limits_config, rules, errors = load_configuration(
        runtime.config_dir
    )
    if errors:
        error_text = "\n".join(str(error) for error in errors[:5])
        await message.answer(runtime.locales.text(locale, "reload.failed", errors=error_text))
        log_event("config_reload_failed", chat_id=chat_id, error_count=len(errors))
        return

    prompt_pools = load_prompt_pools(runtime.config_dir)
    new_locales = load_locales(Path("locales"), bot_config.default_locale)

    runtime.bot_config = bot_config
    runtime.normalization_options = normalization_options
    runtime.limits_config = limits_config
    runtime.rules = rules
    runtime.locales = new_locales
    runtime.llm_reply_prompts = prompt_pools["replies"]
    runtime.llm_daily_prompts = prompt_pools["daily"]
    runtime.llm_cited_prompts = prompt_pools["cited"]
    runtime.llm_digest_prompts = prompt_pools["digest"]
    runtime.llm_secret_prompts = prompt_pools["secret"]

    await message.answer(runtime.locales.text(locale, "reload.success"))
    log_event("config_reloaded", chat_id=chat_id, reaction_rules=len(rules))


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

    # Sleep suppresses everything below (all passive/ambient reactions) --
    # commands like /wake, /help, /status stay available regardless since
    # they're routed to their own handlers above, never reaching here.
    if not is_chat_awake(runtime.db, chat_id):
        return

    if runtime.bot_config.emoji_reactions_enabled:
        emoji = select_emoji_reaction(
            runtime.bot_config.emoji_reaction_pool, runtime.bot_config.emoji_reaction_probability
        )
        if emoji is not None:
            await send_emoji_reaction(bot, message, emoji)
            increment_counter(runtime.db, "global", "emoji_reactions_sent")
            log_event("emoji_reaction_selected", chat_id=chat_id, emoji=emoji)

    # Cited-reply no longer short-circuits the rest of the pipeline: it
    # falls through to word-trigger matching below, so "caciara" plus a
    # word that separately matches an image trigger sends both -- the
    # LLM reply AND the image. It still preempts "segreto" and the
    # ambient reply below (guarded by cited_reply_sent), since those are
    # both alternative text replies -- stacking either alongside the
    # cited reply would just be two competing bot messages for one line.
    cited_reply_sent = False
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
            cited_reply_sent = await _handle_cited_reply(message, runtime, replied_to_bot)

    if (
        not cited_reply_sent
        and runtime.bot_config.llm_enabled
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

    disabled_categories = get_disabled_categories(runtime.db, chat_id)
    active_rules = (
        [rule for rule in runtime.rules if rule.category not in disabled_categories]
        if disabled_categories
        else runtime.rules
    )
    matches = find_matches(message.text, active_rules, runtime.normalization_options)
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
    # trigger or the cited-reply already fired above -- one bot-authored
    # text reply per user message is enough, even though an emoji
    # reaction (not a message) or a word-trigger image (a distinct
    # response type, not competing text) can still land regardless.
    if not cited_reply_sent and runtime.bot_config.llm_enabled and runtime.gemini_api_key:
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


async def _handle_cited_reply(message: Message, runtime: Runtime, replied_to_bot: bool) -> bool:
    """Returns True only if a reply was actually generated and sent/logged --
    callers use this to decide whether to suppress the ambient reply and
    "segreto", not merely whether a citation was detected."""
    chat_id = message.chat.id
    if not runtime.llm_cited_prompts:
        return False

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
        return False

    if runtime.bot_config.llm_dry_run:
        log_event("llm_cited_reply_dry_run", chat_id=chat_id, text=reply_text)
    else:
        await message.answer(reply_text)
    increment_counter(runtime.db, "global", "llm_cited_replies_sent")
    log_event("llm_cited_reply_selected", chat_id=chat_id)
    return True


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
