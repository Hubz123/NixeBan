# -*- coding: utf-8 -*-
from __future__ import annotations
import os

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

current_bot = None

def build_bot() -> commands.Bot:
    global current_bot
    # Fresh Bot instance each run
    allowed_mentions = discord.AllowedMentions(everyone=False, roles=False, users=True, replied_user=False)
    bot = commands.Bot(command_prefix=_get_prefix(), intents=intents, allowed_mentions=allowed_mentions)
    current_bot = bot
    return bot



async def start_bot(token: str):
    bot = build_bot()
    # Wire crucial handlers (optional)
    try:
        from .handlers_crucial import wire_handlers  # type: ignore
    except Exception:
        wire_handlers = None
    if wire_handlers:
        try:
            await wire_handlers(bot)
            log.info("ð§ Crucial handlers wired.")
        except Exception as e:
            log.error("wire_handlers failed: %s", e, exc_info=True)
    # Fresh HTTP session lifecycle per instance
    async with bot:
        try:
            await bot.start(token)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.exception("bot.start failed: %s", e)
            raise

        except asyncio.CancelledError:
            pass
        except Exception:
            pass

async def shutdown():
    global current_bot
    try:
        if current_bot and not current_bot.is_closed():
            await current_bot.close()
    except asyncio.CancelledError:
        pass
    except Exception:
        pass

def get_bot() -> commands.Bot | None:
    return current_bot