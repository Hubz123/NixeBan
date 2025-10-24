# -*- coding: utf-8 -*-
"""
NIXE main.py — ready for Render (web service) & local run.
- Loads .env automatically if available (without breaking Render).
- Exposes /healthz on PORT (Render requirement).
- Disables aiohttp.access spam.
- Ensures bot.process_commands(message) is called.
- Autoloads cogs (prefer project loader; fallback to autodiscover nixe.cogs).
- No manual auto-restart loop (let discord.py handle reconnects).
"""

import os
import sys
import asyncio
import logging
import json
from datetime import datetime, timezone

# --- optional .env loader (works locally; harmless on Render) -----------------
try:
    from dotenv import load_dotenv
    _here = os.path.abspath(os.path.dirname(__file__))
    # Try .env next to main.py, then project root
    load_dotenv(os.path.join(_here, ".env"), override=False)
    load_dotenv(os.path.join(_here, "..", ".env"), override=False)
except Exception:
    pass


# Ensure pHash config module is referenced (for smoketest & runtime)
try:
    import nixe.config_phash as _phash_cfg  # noqa: F401
except Exception:
    _phash_cfg = None
# --- logging: quiet down noisy loggers ---------------------------------------
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s:%(name)s:%(message)s")
log = logging.getLogger("nixe.main")

# show "PyNaCl..." and "logging in using static token" only once
class _OnceFilter(logging.Filter):
    _seen = set()
    _needles = {
        "PyNaCl is not installed, voice will NOT be supported",
        "logging in using static token",
    }
    def filter(self, record):
        msg = record.getMessage()
        for n in self._needles:
            if n in msg:
                if n in self._seen:
                    return False
                self._seen.add(n)
                break
        return True

logging.getLogger("discord.client").addFilter(_OnceFilter())
# mute aiohttp access spam
try:
    logging.getLogger("aiohttp.access").disabled = True
except Exception:
    pass

# --- discord bot --------------------------------------------------------------
import discord
from discord.ext import commands

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True
INTENTS.guilds = True

STARTED_AT = datetime.now(tz=timezone.utc)
_last_ready = None
_loaded_cogs = 0

class NixeBot(commands.Bot):
    async def setup_hook(self):
        """Load cogs before the bot connects."""
        global _loaded_cogs
        # Prefer project-provided loader if available
        try:
            from nixe import cogs_loader as _loader
            _loaded = await _loader.autoload_all(self) if hasattr(_loader, "autoload_all") else _loader.load_all(self)  # type: ignore
            _loaded_cogs = getattr(_loader, "LOADED_COUNT", 0) or (len(_loaded) if isinstance(_loaded, (list, tuple, set)) else _loaded_cogs)
            log.info("✅ Cogs loaded via project loader.")
            return
        except Exception as e:
            log.warning("Project loader unavailable or failed (%r). Falling back to autodiscover.", e)
        # Fallback: autodiscover nixe/cogs/*.py
        try:
            from importlib import import_module
            from pkgutil import iter_modules
            import nixe.cogs as pkg
            base = pkg.__name__ + "."
            for m in iter_modules(pkg.__path__):
                if m.ispkg: 
                    continue
                modname = base + m.name
                try:
                    await self.load_extension(modname)
                    _loaded_cogs += 1
                except Exception as e:
                    log.error("Failed to load %s: %r", modname, e)
            log.info("✅ Autoloaded %d cogs (fallback).", _loaded_cogs)
        except Exception as e:
            log.exception("Autodiscover failed: %r", e)

    async def on_ready(self):
        global _last_ready
        _last_ready = datetime.now(tz=timezone.utc)
        try:
            me = self.user
            log.info("🌐 Bot ready as %s (%s)", getattr(me, "name", "?"), getattr(me, "id", "?"))
        except Exception:
            log.info("🌐 Bot ready.")

    async def on_message(self, message: discord.Message):
        # Always forward to command processor, but ignore other bots
        if getattr(message.author, "bot", False):
            return
        await self.process_commands(message)

bot = NixeBot(command_prefix="!", intents=INTENTS)

# --- tiny HTTP server for Render healthcheck ---------------------------------
from aiohttp import web

async def handle_root(request: web.Request):
    return web.Response(text="NIXE OK", content_type="text/plain")

async def handle_healthz(request: web.Request):
    # health summary
    data = {
        "ok": True,
        "service": "nixe",
        "started_at": STARTED_AT.isoformat(),
        "last_ready": _last_ready.isoformat() if _last_ready else None,
        "loaded_cogs": _loaded_cogs,
        "python": sys.version,
    }
    return web.Response(text=json.dumps(data, ensure_ascii=False), content_type="application/json")

async def start_web(port: int):
    app = web.Application()
    app.add_routes([web.get("/", handle_root), web.get("/healthz", handle_healthz)])
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info("🌐 Web running on port %d; health: /healthz", port)
    try:
        await asyncio.Event().wait()  # run forever
    finally:
        with contextlib.suppress(Exception):
            await runner.cleanup()

# --- glue --------------------------------------------------------------------
import contextlib

async def _run_bot(token: str):
    # Standard start; no manual restart loop (discord.py handles reconnects)
    await bot.start(token, reconnect=True)

async def _main():
    port = int(os.getenv("PORT") or 10000)
    token = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN") or ""
    mode = os.getenv("MODE", "production")
    log.info("🌐 Mode: %s", mode)

    web_task = asyncio.create_task(start_web(port), name="web")
    tasks = [web_task]

    if token:
        bot_task = asyncio.create_task(_run_bot(token), name="bot")
        tasks.append(bot_task)
    else:
        log.error("DISCORD_TOKEN missing — bot will not start. Web healthz still served.")
    
    # Wait for tasks; do not restart automatically
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        log.exception("Fatal error: %r", e)

if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        pass
