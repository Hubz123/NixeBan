# -*- coding: utf-8 -*-
# NIXE Discord shim_runner — with graceful shutdown (no unclosed sessions)
from __future__ import annotations

import os, logging, asyncio, discord
from discord.ext import commands

log = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.presences = True
intents.message_content = True

def _get_prefix() -> str:
    pref = os.getenv("COMMAND_PREFIX")
    if pref:
        return pref
    try:
        from nixe.config import load as _load_cfg  # type: ignore
        pref = (_load_cfg() or {}).get("COMMAND_PREFIX", "!")
    except Exception:
        pref = "!"
    return pref or "!"

allowed_mentions = discord.AllowedMentions(everyone=False, users=True, roles=False, replied_user=False)

bot = commands.Bot(command_prefix=_get_prefix(), intents=intents, allowed_mentions=allowed_mentions)

async def _load_all_cogs(_bot: commands.Bot) -> None:
    loaders = ["nixe.cogs.cogs_loader", "nixe.cogs_loader"]
    last_err = None
    for mod in loaders:
        try:
            modobj = __import__(mod, fromlist=["load_cogs"])
            if hasattr(modobj, "load_cogs"):
                await modobj.load_cogs(_bot)
                return
        except Exception as e:
            last_err = e
    if last_err:
        log.error("Failed to load cogs (%s): %s", loaders, last_err, exc_info=True)

@bot.event
async def on_ready():
    try:
        log.info("✅ Bot login as %s (%s)", bot.user, bot.user.id if bot.user else "?")
    except Exception:
        log.info("✅ Bot login.")

@bot.event
async def setup_hook():
    await _load_all_cogs(bot)
    if os.getenv("METRICS_DISABLE", "0") not in ("1", "true", "TRUE"):
        for ext in ["nixe.cogs.live_metrics_push", "nixe.metrics.live_metrics_push"]:
            try:
                if ext not in bot.extensions:
                    await bot.load_extension(ext)
                    log.info("✅ Loaded metrics cog: %s", ext)
                    break
            except Exception:
                pass

async def start_bot(token: str | None = None):
    token = (token or os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN") or "").strip()
    if not token:
        try:
            from nixe.config import load as _load_cfg  # type: ignore
            token = (_load_cfg() or {}).get("BOT_TOKEN", "") or ""
        except Exception:
            token = ""
    token = token.strip()
    if not token:
        raise RuntimeError("DISCORD_TOKEN / BOT_TOKEN kosong (ENV atau module config).")

    try:
        await bot.start(token)
    except asyncio.CancelledError:
        pass
    finally:
        try:
            await bot.close()
        except Exception:
            pass

async def shutdown():
    """Gracefully close the Discord client to avoid unclosed sessions."""
    try:
        if not bot.is_closed():
            await bot.close()
    except Exception:
        pass

def get_bot() -> commands.Bot:
    return bot