from __future__ import annotations
import os, asyncio, logging
from logging.config import dictConfig

def setup_logging():
    level = os.getenv("LOG_LEVEL", os.getenv("PYTHON_LOGLEVEL", "INFO")).upper()
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"std": {"format": "%(asctime)s %(levelname)s:%(name)s:%(message)s"}},
        "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "std", "level": level}},
        "root": {"handlers": ["console"], "level": level},
    })
    # Tweak discord logger
    try:
        import discord
        if hasattr(discord.utils, "setup_logging"):
            discord.utils.setup_logging(level=(logging.DEBUG if level=="DEBUG" else logging.INFO))
    except Exception:
        pass
    # Raise levels for our namespaces if DEBUG
    for ns in ["nixe", "nixe.cogs", "nixe.cogs.lucky_pull_guard", "nixe.cogs.phash_db_board", "nixe.cogs_loader"]:
        logging.getLogger(ns).setLevel(level)

async def start_bot():
    # bridge to shim_runner
    from nixe.discord.shim_runner import start_bot as _start
    token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN") or ""
    return await _start(token)

def main():
    setup_logging()
    asyncio.run(start_bot())

if __name__ == "__main__":
    main()
