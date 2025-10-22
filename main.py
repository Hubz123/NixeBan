from __future__ import annotations
import asyncio
import logging
import sys
import uvicorn
from nixe.config.env import settings, load_dotenv_verbose

# Show INFO logs (cogs, startup, etc.) on Render
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
            return ('/healthz' not in msg) and ('GET /healthz' not in msg) and ('"/healthz"' not in msg)

    for name in ('uvicorn.access', 'uvicorn.error', 'werkzeug'):
        _logging.getLogger(name).addFilter(_HealthzFilter())

async def run_uvicorn_once() -> None:
    cfg = uvicorn.Config(
        'nixe.web.asgi:app',
        host=settings().HOST,
        port=settings().PORT,
        log_level='info',     # keep info-level startup logs
        access_log=True,      # access logs ON, but /healthz filtered by our filter
        workers=1,
    )
    server = uvicorn.Server(cfg)
    await server.serve()

async def supervise_web(log: logging.Logger) -> None:
    while True:
        try:
            log.info('Starting Uvicorn web server...')
            await run_uvicorn_once()
            log.warning('Uvicorn web server stopped; restarting in 3s…')
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error('Uvicorn crashed: %r', e, exc_info=True)
        await asyncio.sleep(3)
    log.info('Web supervisor exiting.')

async def supervise_bot(log: logging.Logger) -> None:
    from nixe.runner import shim_runner
    while True:
        try:
            log.info('Starting Discord bot task...')
            await shim_runner.start_bot()
            log.warning('Discord bot task ended; restarting in 5s…')
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error('Discord bot crashed: %r', e, exc_info=True)
        await asyncio.sleep(5)
    log.info('Bot supervisor exiting.')

async def amain_concurrent() -> None:
    load_dotenv_verbose()
    _install_healthz_log_filter()
    log = logging.getLogger('entry.main')
    log.info('🤖 Starting NIXE multiprocess (Discord + Web)...')

    web_task = asyncio.create_task(supervise_web(log), name='uvicorn-supervisor')
    bot_task = asyncio.create_task(supervise_bot(log), name='discord-bot-supervisor')

    # Keep process alive until terminated; avoid awaiting web_task directly (prevents CancelledError)
    stop = asyncio.Event()
    try:
        await stop.wait()
    except asyncio.CancelledError:
        pass
    finally:
        for t in (web_task, bot_task):
            t.cancel()
        await asyncio.gather(web_task, bot_task, return_exceptions=True)
        log.info('Shutdown requested by user.')

if __name__ == '__main__':
    try:
        asyncio.run(amain_concurrent())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger('entry.main').info('Shutdown requested by user.')
