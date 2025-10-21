from __future__ import annotations
import os
import logging
import asyncio
import inspect
from typing import Optional

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

def _read_token() -> Optional[str]:
    for k in ("DISCORD_TOKEN", "DISCORD_BOT_TOKEN", "BOT_TOKEN"):
        v = (os.getenv(k) or "").strip()
        if v:
            return v
    return None

def create_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True  # required for on_message guards
    bot = commands.Bot(command_prefix=os.getenv("NIXE_PREFIX", "!"), intents=intents)
    return bot

async def _maybe_load_extension(bot: commands.Bot, name: str) -> None:
    try:
        ret = bot.load_extension(name)
        if inspect.isawaitable(ret):
            await ret
        log.info("Loaded extension: %s", name)
    except commands.ExtensionAlreadyLoaded:
        log.debug("Extension already loaded: %s", name)
    except Exception:
        log.warning("[shim_runner] failed to load %s", name, exc_info=True)

async def start_discord_bot() -> None:
    token = _read_token()
    bot = create_bot()

    # Load cogs loader extension; it will auto-load all cogs on_ready
    await _maybe_load_extension(bot, "nixe.cogs.cogs_loader")

    if not token:
        log.error("[shim_runner] DISCORD_TOKEN / BOT_TOKEN not set; Discord bot will not start.")
        # Keep task alive so main process continues (web can still run)
        while True:
            await asyncio.sleep(3600)
    else:
        log.info("[shim_runner] logging in using static token")
        await bot.start(token)
