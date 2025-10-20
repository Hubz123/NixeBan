# scripts/graceful_probe.py
# Test graceful shutdown without Discord token.
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nixe.helpers.graceful import install_graceful_shutdown

class FakeBot:
    async def close(self):
        print("[GRACEFUL] FakeBot.close() called")
        await asyncio.sleep(0.2)

async def main():
    bot = FakeBot()
    install_graceful_shutdown(bot, timeout=5.0)
    print("[GRACEFUL] Running. Press Ctrl+C to test shutdown...")
    # keep running until signal
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError, RuntimeError):
        # Normal ketika handler membatalkan task utama agar keluar rapi
        print("[GRACEFUL] Shutdown complete.")
