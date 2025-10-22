
from __future__ import annotations
import asyncio
import logging
import uvicorn

from nixe.config.env import settings, load_dotenv_verbose

log = logging.getLogger("entry.main")

async def run_uvicorn() -> None:
    # Run ASGI: nixe.web.asgi:app
    config = uvicorn.Config("nixe.web.asgi:app", host=settings().HOST, port=settings().PORT, log_level="info", workers=1)
    server = uvicorn.Server(config)
    await server.serve()

async def supervise_bot(log):
    from nixe.runner import shim_runner
    while True:
        try:
            log.info("Starting Discord bot task...")
            await shim_runner.start_bot()
            log.warning("Discord bot task ended; restarting in 5s…")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.error("Discord bot crashed: %r", e, exc_info=True)
        await asyncio.sleep(5)

async def amain_concurrent():
    load_dotenv_verbose()
    log.info("🤖 Starting NIXE multiprocess (Discord + Web)...")
    log.info("Starting Uvicorn web server...")
    web_task = asyncio.create_task(run_uvicorn(), name="uvicorn-server")
    bot_task = asyncio.create_task(supervise_bot(log), name="discord-bot-supervisor")
    # Keep web as the owning lifecycle so /healthz stays up
    done, pending = await asyncio.wait({web_task}, return_when=asyncio.FIRST_COMPLETED)
    # Cancel bot on shutdown
    for t in pending:
        t.cancel()
    await asyncio.gather(*pending, return_exceptions=True)

if __name__ == "__main__":
    try:
        asyncio.run(amain_concurrent())
    except KeyboardInterrupt:
        log.info("Shutdown requested by user.")
