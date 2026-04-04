"""Slash-command router.

Ports the command surface from the original ``telegram/client.ts``:

* ``/start``     - greeting / onboarding.
* ``/register``  - activate the bot in a group (groups only).
* ``/schedule``  - create a Watchout Protocol research job.
* ``/schedules`` - list this chat's jobs.
* ``/pause``     - toggle a job active/paused (by short-id prefix).
* ``/remove``    - delete a job (by short-id prefix).

Handlers receive ``repos`` (and other workflow data) as keyword arguments
injected by the dispatcher.
"""

from __future__ import annotations

import re

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from gisst.db.repositories import Repositories
from gisst.logging import get_logger
from gisst.models import ChatType, ScheduleJobState

log = get_logger("telegram.commands")

router = Router(name="commands")

# Cadence like "every 4h" / "every 30m"; digest like "digest 20:00".
_EVERY_RE = re.compile(r"every\s+\d+\s*[hm]", re.IGNORECASE)
_DIGEST_RE = re.compile(r"digest\s+(\d{1,2}:\d{2})", re.IGNORECASE)
_TOPIC_SPLIT_RE = re.compile(r"\s+every\s+|\s+digest\s+", re.IGNORECASE)

_DEFAULT_CADENCE = "every 4h"
_DEFAULT_DIGEST_TIME = "20:00"

_START_TEXT = (
    "👋 I'm Scout, your Gisst research agent.\n\n"
    "Ask me anything - I'll search the web and give you cited answers.\n\n"
    "In groups: add me, then send /register to activate."
)

_REGISTER_TEXT = (
    "✅ Gisst activated in this group!\n\n"
    "I'll respond to:\n"
    "• Messages starting with !\n"
    "• Messages mentioning Scout or Gisst\n"
    "• Direct replies to my messages\n\n"
    "Try: !help to see what I can do."
)

_SCHEDULE_USAGE = (
    "Usage: /schedule <topic> [cadence] [digest time]\n\n"
    "Examples:\n"
    "  /schedule F1 News\n"
    "  /schedule AI Policy every 2h digest 20:00\n"
    "  /schedule Climate Tech every 6h digest 09:00\n\n"
    "Defaults: crawl every 4h, digest at 20:00"
)


def _is_group(chat_type: str) -> bool:
    return chat_type in (ChatType.GROUP.value, ChatType.SUPERGROUP.value)


def _parse_schedule_args(args: str) -> tuple[str, str, str]:
    """Parse ``"<topic> [every Nh] [digest HH:MM]"`` into (topic, cadence, digest_time).

    Faithful port of the parsing in ``client.ts``: the topic is everything before
    the first ``every`` / ``digest`` keyword (or the whole string when neither is
    present); cadence and digest time fall back to the defaults.
    """
    topic = args
    cadence = _DEFAULT_CADENCE
    digest_time = _DEFAULT_DIGEST_TIME

    every_match = _EVERY_RE.search(args)
    digest_match = _DIGEST_RE.search(args)

    if every_match:
        cadence = every_match.group(0)
        topic = args[: every_match.start()].strip()
    if digest_match:
        digest_time = digest_match.group(1)
        if not every_match:
            topic = args[: digest_match.start()].strip()
    if not topic:
        topic = _TOPIC_SPLIT_RE.split(args)[0].strip()

    return topic, cadence, digest_time


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Greet the user and explain group activation."""
    await message.answer(_START_TEXT)


@router.message(Command("register"))
async def handle_register(message: Message, repos: Repositories) -> None:
    """Activate the bot in the current group (no-op in private chats)."""
    if not message.chat or not _is_group(message.chat.type):
        await message.answer("This command is for groups. Just DM me directly!")
        return

    chat_id = str(message.chat.id)
    registered_by = str(message.from_user.id) if message.from_user else None
    await repos.groups.add(chat_id, registered_by=registered_by)
    await message.answer(_REGISTER_TEXT)


@router.message(Command("schedule"))
async def handle_schedule(message: Message, command: CommandObject, repos: Repositories) -> None:
    """Create a recurring Watchout Protocol research job."""
    args = (command.args or "").strip()
    if not args:
        await message.answer(_SCHEDULE_USAGE)
        return

    topic, cadence, digest_time = _parse_schedule_args(args)
    if not topic:
        await message.answer(_SCHEDULE_USAGE)
        return

    job = ScheduleJobState(
        topic=topic,
        keywords=topic.split(),
        cadence=cadence,
        digest_time=digest_time,
        chat_id=str(message.chat.id),
        created_by=str(message.from_user.id) if message.from_user else "",
    )
    await repos.jobs.add(job)

    await message.answer(
        f'✅ Scheduled: "{topic}"\n\n'
        f"• Crawl: {cadence}\n"
        f"• Digest: daily at {digest_time} UTC\n"
        f"• ID: {job.short_id}\n\n"
        f"I'll research this topic throughout the day and send you a summary "
        f"at {digest_time}."
    )


@router.message(Command("schedules"))
async def handle_schedules(message: Message, repos: Repositories) -> None:
    """List the scheduled jobs belonging to this chat."""
    chat_jobs = await repos.jobs.list_for_chat(str(message.chat.id))
    if not chat_jobs:
        await message.answer("No scheduled jobs for this chat. Create one with /schedule")
        return

    lines = []
    for i, job in enumerate(chat_jobs, start=1):
        status = "🟢" if job.active else "⏸️"
        lines.append(
            f'{status} {i}. "{job.topic}" - {job.cadence}, digest at {job.digest_time}\n'
            f"   ID: {job.short_id}"
        )

    body = "\n\n".join(lines)
    await message.answer(f"Scheduled jobs:\n\n{body}\n\nCommands: /pause <id> · /remove <id>")


@router.message(Command("pause"))
async def handle_pause(message: Message, command: CommandObject, repos: Repositories) -> None:
    """Toggle a job active/paused, matched by short-id prefix."""
    prefix = (command.args or "").strip()
    if not prefix:
        await message.answer("Usage: /pause <job-id>")
        return

    job = await repos.jobs.find_by_prefix(prefix)
    if job is None:
        await message.answer(f'No job found with ID starting with "{prefix}"')
        return

    updated = await repos.jobs.toggle(job.id)
    is_active = updated.active if updated else not job.active
    label = "▶️ Resumed" if is_active else "⏸️ Paused"
    await message.answer(f'{label}: "{job.topic}"')


@router.message(Command("remove"))
async def handle_remove(message: Message, command: CommandObject, repos: Repositories) -> None:
    """Delete a job, matched by short-id prefix."""
    prefix = (command.args or "").strip()
    if not prefix:
        await message.answer("Usage: /remove <job-id>")
        return

    job = await repos.jobs.find_by_prefix(prefix)
    if job is None:
        await message.answer(f'No job found with ID starting with "{prefix}"')
        return

    await repos.jobs.remove(job.id)
    await message.answer(f'🗑️ Removed: "{job.topic}"')
