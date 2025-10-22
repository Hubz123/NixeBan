
from __future__ import annotations
import asyncio, logging
import uvicorn
from nixe.config.env import settings, load_dotenv_verbose

log = logging.getLogger("entry.main")

async def run_uvicorn() -> None:
    cfg = uvicorn.Config(
        "nixe.web.asgi:app",
        host=settings().HOST,
        port=settings().PORT,
        log_level="warning",
        workers=1,
        access_log=settings().ACCESS_LOG,
    )
    server = uvicorn.Server(cfg)
    await server.serve()

async def supervise_bot(logger):
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

async def amain_concurrent():
    load_dotenv_verbose()
    log.info("🤖 Starting NIXE multiprocess (Discord + Web)...")
    log.info("Starting Uvicorn web server...")
    web_task = asyncio.create_task(run_uvicorn(), name="uvicorn-server")
    bot_task = asyncio.create_task(supervise_bot(log), name="discord-bot-supervisor")
    # Keep web alive no matter what; only wait for web_task
    done, pending = await asyncio.wait({web_task}, return_when=asyncio.FIRST_COMPLETED)
    for t in pending:
        t.cancel()
    await asyncio.gather(*pending, return_exceptions=True)

if __name__ == "__main__":
    try:
        asyncio.run(amain_concurrent())
    except KeyboardInterrupt:
        log.info("Shutdown requested by user.")
