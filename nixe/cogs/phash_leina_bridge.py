
from __future__ import annotations
import os, re, asyncio, logging
from typing import Optional, Set, List

import discord
from discord.ext import commands, tasks

log = logging.getLogger("nixe.cogs.phash_leina_bridge")

# --- Config (defaults baked-in; can override via ENV) ---
LEINA_SOURCE_THREAD_ID = int(os.getenv("LEINA_SOURCE_THREAD_ID", os.getenv("PHASH_SOURCE_THREAD_ID", "1409949797313679492")))
LEINA_SOURCE_CHANNEL_ID = int(os.getenv("LEINA_SOURCE_CHANNEL_ID", "0"))
LEINA_TITLE = os.getenv("LEINA_DB_TITLE", "SATPAMBOT_PHASH_DB_V1")
LEINA_JSON_KEY = os.getenv("LEINA_JSON_KEY", "phash")

DEST_DB_THREAD_ID = int(os.getenv("PHASH_DB_THREAD_ID", "1430048839556927589"))
IMPORT_MARKER = os.getenv("LEINA_IMPORT_MARKER", "[leina-phash-import]")
TICK_SEC = int(os.getenv("LEINA_BRIDGE_EVERY_SEC", "300"))
MAX_BYTES = int(os.getenv("LEINA_IMPORT_MAX_BYTES", "1800"))

HEX16 = re.compile(r"\b[0-9a-f]{16}\b")

def _collect_tokens(text: str, out: Set[str]) -> None:
    if not text:
        return
    for tok in HEX16.findall(text.lower()):
        out.add(tok)

async def _ensure_unarchived(th: discord.Thread) -> None:
    try:
        if getattr(th, "archived", False):
            await th.edit(archived=False)
    except Exception:
        pass

def _render_import_message(tokens: List[str], title: str, key: str) -> str:
    arr = ",\n".join([f"    \"{t}\"" for t in tokens])
    content = (
        f"{title}\n" +
        "```json\n" +
        "{\n" +
        f"  \"{key}\": [\n" +
        f"{arr}\n" +
        "  ]\n" +
        "}\n" +
        "```" +
        f" {IMPORT_MARKER}"
    )
    return content
async def setup(bot: commands.Bot):
    await bot.add_cog(PhashLeinaBridge(bot))
def _render_import_message(tokens: List[str], title: str, key: str) -> str:
    body_lines = [f"    \"{t}\"" for t in tokens]
    arr = ",\n".join(body_lines)
    content = (
        f"{title}\n"
        "```json\n"
        "{\n"
        f"  \"{key}\": [\n"
        f"{arr}\n"
        "  ]\n"
        "}\n"
        "```"
        f" {IMPORT_MARKER}"
    )
    return content