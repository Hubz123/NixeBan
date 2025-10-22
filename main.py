from __future__ import annotations
import asyncio
import logging
import sys
import uvicorn
from nixe.config.env import settings, load_dotenv_verbose

# Ensure INFO logs appear on Render (cogs, startup, etc.)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
    stream=sys.stdout,
)

def _install_healthz_log_filter() -> None:
    """Hide ONLY /healthz lines in access/error logs; keep everything else visible."""
    import logging as _logging

    class _HealthzFilter(_logging.Filter):
        def filter(self, record):
            try:
                msg = record.getMessage()
            except Exception:
                msg = str(record)
            return (
                "/healthz" not in msg
                and "GET /healthz" not in msg
                and '"/healthz"' not in msg
            )

    for name in ("uvicorn.access", "uvicorn.error", "werkzeug"):
        _logging.getLogger(name).addFilter(_HealthzFilter())

async def run_uvicorn() -> None:
    cfg = uvicorn.Config(
        "nixe.web.asgi:app",
        host=settings().HOST,
        port=settings().PORT,
        log_level="info",        # show info-level startup logs
        workers=1,
        access_log=True,          # keep access logs (except /healthz via filter)
    )
    server = uvicorn.Server(cfg)
    await server.serve()

async def supervise_bot(logger: logging.Logger) -> None:
    from nixe.runner import shim_runner
    while True:
        try:
            logger.info("Starting Discord bot task...")
            await shim_runner.start_bot()
            logger.warning("Discord bot task ended; restarting in 5s…")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Discord bot crashed: %r", e, exc_info=True)
        await asyncio.sleep(5)

async def amain_concurrent() -> None:
    load_dotenv_verbose()
    _install_healthz_log_filter()
    log = logging.getLogger("entry.main")

    log.info("🤖 Starting NIXE multiprocess (Discord + Web)...")
    log.info("Starting Uvicorn web server...")
    web_task = asyncio.create_task(run_uvicorn(), name="uvicorn-server")
    bot_task = asyncio.create_task(supervise_bot(log), name="discord-bot-supervisor")

    # Keep the web server as the owning lifecycle so /healthz stays up 24/7
    done, pending = await asyncio.wait({web_task}, return_when=asyncio.FIRST_COMPLETED)

    # On shutdown, cancel the supervisor gracefully
    for t in pending:
        t.cancel()
    await asyncio.gather(*pending, return_exceptions=True)

if __name__ == "__main__":
    try:
        asyncio.run(amain_concurrent())
    except KeyboardInterrupt:
        logging.getLogger("entry.main").info("Shutdown requested by user.")
