# Single-run launcher: no auto-restart, clean Ctrl+C exit
import os, asyncio, logging
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
from nixe.discord import shim_runner

async def _main():
    token = os.environ.get("DISCORD_TOKEN", "").strip()
    if not token:
        logging.error("DISCORD_TOKEN env var is missing; abort.")
        return
    await shim_runner.start_bot(token)

if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        print("Shutdown requested; exiting without auto-restart.")
