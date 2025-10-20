#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import asyncio
import logging
from typing import Optional

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(levelname)s:%(name)s:%(message)s",
)
log = logging.getLogger("entry.main")

def _load_dotenv_early() -> None:
    try:
        from dotenv import load_dotenv, find_dotenv  # type: ignore
    except Exception:
        return
    for f in [os.getenv("ENV_FILE"), ".env", "Nixe.env", "NIXE.env", "SatpamBot.env", "satpambot.env"]:
        if f and os.path.exists(f):
            load_dotenv(f, override=False)
            print(f"✅ Loaded env file: {f}")
            break
    else:
        auto = find_dotenv(filename=".env", usecwd=True)
        if auto:
            load_dotenv(auto, override=False)
            print(f"✅ Loaded env file: {auto}")

_load_dotenv_early()

def _cfg_get(key: str, default=None):
    try:
        from nixe.config import load as _load_cfg  # type: ignore
        cfg = _load_cfg()
        if isinstance(cfg, dict):
            return cfg.get(key, default)
    except Exception:
        pass
    return default

def _get_token() -> Optional[str]:
    tok = os.environ.get("DISCORD_TOKEN") or os.environ.get("BOT_TOKEN")
    if not tok:
        tok = _cfg_get("BOT_TOKEN", "") or ""
    tok = (tok or "").strip()
    return tok or None

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", os.getenv("WEB_PORT", "10000")))
WEB_THREADS = int(os.getenv("WEB_THREADS", "8"))
WEB_LOG_LEVEL = os.getenv("WEB_LOG_LEVEL", "WARNING").upper()

async def _run_web_async() -> None:
    try:
        import uvicorn  # type: ignore
        app_ref = None
        try:
            from nixe.web.asgi import app as _  # type: ignore
            app_ref = ("nixe.web.asgi", "app")
        except Exception:
            pass
        if app_ref is None:
            try:
                from app import app as _  # type: ignore
                app_ref = ("app", "app")
            except Exception:
                pass
        if app_ref is not None:
            log.info("🌐 Serving web (uvicorn) on %s:%s", HOST, PORT)
            config = uvicorn.Config(f"{app_ref[0]}:{app_ref[1]}", host=HOST, port=PORT, log_level=WEB_LOG_LEVEL.lower(), lifespan="auto")
            server = uvicorn.Server(config)
            await server.serve()
            return
    except Exception:
        pass

    try:
        from waitress import serve as waitress_serve  # type: ignore
        try:
            from app import app as flask_app  # type: ignore
            logging.getLogger("waitress").setLevel(getattr(logging, WEB_LOG_LEVEL, logging.WARNING))
            log.info("🌐 Serving web (waitress) on %s:%s", HOST, PORT)
            await asyncio.get_event_loop().run_in_executor(None, lambda: waitress_serve(flask_app, host=HOST, port=PORT, threads=WEB_THREADS))
            return
        except Exception:
            pass
    except Exception:
        pass

    try:
        from wsgiref.simple_server import make_server, WSGIRequestHandler
        from app import app as wsgi_app  # type: ignore

        class QuietHandler(WSGIRequestHandler):
            def log_message(self, fmt, *args):
                if WEB_LOG_LEVEL == "DEBUG":
                    super().log_message(fmt, *args)

        log.info("🌐 Serving web (wsgiref) on %s:%s", HOST, PORT)
        def _serve():
            httpd = make_server(HOST, PORT, wsgi_app, handler_class=QuietHandler)
            httpd.serve_forever()
        await asyncio.get_event_loop().run_in_executor(None, _serve)
    except Exception:
        logging.getLogger("entry.main").warning("🌐 Web app not found; running without web")

async def _run_bot_async(token: str) -> None:
    # Prefer nixe.discord.shim_runner (requires nixe/discord/__init__.py)
    try:
        from nixe.discord import shim_runner  # type: ignore
    except Exception as e1:
        # Fallback flat layout
        try:
            from nixe import shim_runner  # type: ignore
        except Exception as e2:
            raise ImportError(f"Cannot import shim_runner. Tried nixe.discord & nixe root. Errors: {e1!r} / {e2!r}")

    await shim_runner.start_bot(token)

async def main() -> None:
    web_enabled = os.getenv("RUN_WEB", "1") != "0"
    token = _get_token()

    if web_enabled:
        log.info("🌐 Web is enabled (HOST=%s PORT=%s)", HOST, PORT)
    else:
        log.info("🌐 Web disabled by RUN_WEB=0")

    if not token:
        log.error("DISCORD_TOKEN/BOT_TOKEN env/config is missing; running WEB-ONLY mode (bot skipped).")
        if web_enabled:
            await _run_web_async()
        return

    tasks = []
    if web_enabled:
        tasks.append(asyncio.create_task(_run_web_async(), name="web"))
    tasks.append(asyncio.create_task(_run_bot_async(token), name="bot"))

    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    except asyncio.CancelledError:
        pass
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()
        try:
            from nixe.discord import shim_runner as _shim  # type: ignore
            await _shim.shutdown()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass