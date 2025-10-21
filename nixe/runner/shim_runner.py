
from __future__ import annotations
import os
import logging
import asyncio
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

def _prefix() -> str:
    p = os.getenv("COMMAND_PREFIX")
    return p if p else "!"

def create_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix=_prefix(), intents=intents)
    return bot

async def _maybe_load_extension(bot: commands.Bot, name: str) -> None:
    try:
        await bot.load_extension(name)
        # Log using the exact loader logger for consistent output
        logging.getLogger("nixe.cogs_loader").info("✅ Loaded cog: %s", name)
    except commands.ExtensionAlreadyLoaded:
        logging.getLogger("nixe.cogs_loader").info("✅ Loaded cog: %s", name)
    except Exception as e:
        log.exception("Failed to load extension %s: %s", name, e)

async def start_bot():
    token = _read_token()
    bot = create_bot()

    # Load crucial display/handlers first
    await _maybe_load_extension(bot, "nixe.discord.handlers_crucial")

    # Load our loader that will auto-load all cogs (uses nixe.cogs_loader logger)
    await _maybe_load_extension(bot, "nixe.cogs_loader")

    if not token:
        log.error("[shim_runner] DISCORD_TOKEN / BOT_TOKEN not set; Discord bot will not start.")
        # Keep task alive so main process continues (web can still run)
        while True:
            await asyncio.sleep(3600)
    else:
        log.info("[shim_runner] logging in using static token")
        await bot.start(token)
