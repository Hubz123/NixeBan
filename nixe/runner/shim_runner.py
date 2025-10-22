
from __future__ import annotations
import logging, os, asyncio
import discord
from discord.ext import commands
from nixe.config.env import settings

log = logging.getLogger("nixe.runner.shim_runner")

def _get_token() -> str | None:
    return settings().token()

async def _maybe_load_extension(bot: commands.Bot, name: str) -> None:
    try:
        await bot.load_extension(name)
    except Exception:
        pass

async def start_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    # Load crucial handlers and loader
    await _maybe_load_extension(bot, "nixe.discord.handlers_crucial")
    await _maybe_load_extension(bot, "nixe.cogs_loader")

    token = _get_token()
    if not token:
        raise RuntimeError("DISCORD_TOKEN / BOT_TOKEN missing in environment")
    log.info("[shim_runner] logging in using static token")
    print("INFO:discord.client: logging in using static token")  # keep legacy line
    await bot.start(token)
