from __future__ import annotations
# nixe/helpers/phash_board.py
# Helper untuk EDIT-ONLY pinned DB pHash

import json, time, contextlib
import discord
from nixe.config_phash import (
    PHASH_DB_THREAD_ID, PHASH_DB_MESSAGE_ID, PHASH_DB_STRICT_EDIT,
    PHASH_DB_MAX_ITEMS, PHASH_BOARD_EDIT_MIN_INTERVAL,
)

_last_edit_ts = 0.0
_discovered_msg_id = 0

def _parse_tokens_from_pinned(text: str) -> set[str]:
    text = (text or "").strip()
    toks: set[str] = set()
    if not text:
        return toks
    with contextlib.suppress(Exception):
        t = text
        if t.startswith("```"):
            t = t.strip("`").strip()
            if t.startswith("json"):
                t = t[4:]
        data = json.loads(t)
        if isinstance(data, dict) and isinstance(data.get("phash"), list):
            for x in data["phash"]:
                s = str(x).strip().lower()
                if s:
                    toks.add(s[:16])
            return toks
    for part in text.replace("\\n", " ").split():
        s = part.strip().lower()
        if len(s) in (16, 64):
            toks.add(s[:16])
    return toks

def looks_like_phash_db(text: str) -> bool:
    if not text:
        return False
    s = text.strip()
    if "[phash-db-board]" in s.lower():
        return True
    with contextlib.suppress(Exception):
        t = s
        if t.startswith("```"):
            t = t.strip("`").strip()
            if t.startswith("json"):
                t = t[4:]
        data = json.loads(t)
        return isinstance(data, dict) and "phash" in data
    return len(_parse_tokens_from_pinned(s)) >= 1

async def discover_db_message_id(bot: discord.Client) -> int:
    global _discovered_msg_id
    if _discovered_msg_id:
        return _discovered_msg_id
    if not PHASH_DB_THREAD_ID:
        return 0
    ch = bot.get_channel(PHASH_DB_THREAD_ID) or await bot.fetch_channel(PHASH_DB_THREAD_ID)
    with contextlib.suppress(Exception):
        for m in await ch.pins():
            if looks_like_phash_db(getattr(m, "content", "")):
                _discovered_msg_id = int(m.id)
                return _discovered_msg_id
    with contextlib.suppress(Exception):
        async for m in ch.history(limit=500):
            if looks_like_phash_db(getattr(m, "content", "")):
                _discovered_msg_id = int(m.id)
                return _discovered_msg_id
    return 0

async def get_pinned_db_message(bot: discord.Client) -> discord.Message | None:
    msg_id = PHASH_DB_MESSAGE_ID or _discovered_msg_id or await discover_db_message_id(bot)
    if not (PHASH_DB_THREAD_ID and msg_id):
        return None
    ch = bot.get_channel(PHASH_DB_THREAD_ID) or await bot.fetch_channel(PHASH_DB_THREAD_ID)
    return await ch.fetch_message(msg_id)

async def edit_pinned_db(bot: discord.Client, tokens: set[str]) -> bool:
    """Edit pinned DB (EDIT-ONLY). Tidak pernah membuat message baru."""
    global _last_edit_ts
    if PHASH_DB_STRICT_EDIT and not (PHASH_DB_THREAD_ID and (PHASH_DB_MESSAGE_ID or _discovered_msg_id)):
        return False
    if time.time() - _last_edit_ts < PHASH_BOARD_EDIT_MIN_INTERVAL:
        return False
    msg = await get_pinned_db_message(bot)
    if not msg:
        return False
    items = sorted(set(tokens))[:PHASH_DB_MAX_ITEMS]
    body = ",\n".join(f'    "{t}"' for t in items)
    content = "```json\n{\n  \"phash\": [\n" + body + "\n  ]\n}\n```\n[phash-db-board]"
    if (msg.content or "").strip() == content.strip():
        return True
    await msg.edit(content=content)
    _last_edit_ts = time.time()
    return True
