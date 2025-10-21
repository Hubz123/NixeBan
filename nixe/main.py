from __future__ import annotations
import asyncio, os

async def start_bot():
    # bridge to shim_runner
    from nixe.discord.shim_runner import start_bot as _start
    token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN") or ""
    return await _start(token)

def main():
    # sync entry for old scripts
    asyncio.run(start_bot())

if __name__ == "__main__":
    main()