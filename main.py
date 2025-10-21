#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import logging
import logging.config
import os

# Load .env if present
try:
    from dotenv import load_dotenv, find_dotenv
    _env = find_dotenv(usecwd=True) or ".env"
    if _env and os.path.exists(_env):
        load_dotenv(_env, override=False)
        print(f"✅ Loaded env file: {_env}")
except Exception:
    pass

def _setup_logging() -> None:
    # Use the classic format: LEVEL:logger: message — ensures newline per record
    fmt = "%(levelname)s:%(name)s: %(message)s"
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": fmt},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {
            # Root logger
            "": {"handlers": ["console"], "level": level},
            # Make discord/uvicorn obey the same format
            "discord": {"level": level, "handlers": ["console"], "propagate": False},
            "uvicorn": {"level": level, "handlers": ["console"], "propagate": False},
            "uvicorn.error": {"level": level, "handlers": ["console"], "propagate": False},
            "uvicorn.access": {"level": os.getenv("UVICORN_ACCESS_LEVEL", "INFO").upper(), "handlers": ["console"], "propagate": False},
        },
    }
    logging.config.dictConfig(log_config)

_setup_logging()
log = logging.getLogger("entry.main")

async def run_uvicorn() -> None:
    import uvicorn
    # Pass a compatible log_config so uvicorn uses the same format
    fmt = "%(levelname)s:%(name)s: %(message)s"
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    uvlog = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"standard": {"format": fmt}},
        "handlers": {"default": {"class": "logging.StreamHandler", "formatter": "standard", "stream": "ext://sys.stdout"}},
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": level},
            "uvicorn.error": {"handlers": ["default"], "level": level, "propagate": False},
            "uvicorn.access": {"handlers": ["default"], "level": os.getenv("UVICORN_ACCESS_LEVEL", "INFO").upper(), "propagate": False},
        },
    }
    log.info("Starting Uvicorn web server...")
    config = uvicorn.Config(
        "nixe.web.asgi:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "10000")),
        log_level=level.lower(),
        lifespan="off",
        log_config=uvlog,
    )
    server = uvicorn.Server(config)
    await server.serve()

async def run_discord() -> None:
    from nixe.runner.shim_runner import start_discord_bot
    log.info("Starting Discord bot task...")
    await start_discord_bot()

async def amain() -> None:
    log.info("🤖 Starting NIXE multiprocess (Discord + Web)...")
    while True:
        tasks = [asyncio.create_task(run_uvicorn()), asyncio.create_task(run_discord())]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        crashed = False
        for res in results:
            if isinstance(res, BaseException):
                crashed = True
                log.error("Background task crashed: %r", res, exc_info=True)
        if not crashed:
            break
        await asyncio.sleep(1.0)

if __name__ == "__main__":
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        log.info("Shutdown requested by user.")
