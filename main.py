# main.py — Render Web + Discord bot + quiet /healthz
import os, asyncio, logging
from fastapi import FastAPI
import uvicorn
from nixe.web.quiet_healthz import install_fastapi_quiet_healthz, install_quiet_accesslog
from nixe import config as cfg

import discord
from discord.ext import commands

# Logging
C = cfg.load()
level = getattr(logging, str(C.log_level).upper(), logging.INFO)
logging.basicConfig(level=level, format=os.getenv("LOG_FORMAT", "%(levelname)s:%(name)s:%(message)s"))
install_quiet_accesslog()

# FastAPI app + /healthz (204) — silent in accesslog
app = FastAPI()
install_fastapi_quiet_healthz(app)

# Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def _load_cogs():
    for ext in [
        "nixe.cogs.phash_inbox_watcher",
        "nixe.cogs.image_phish_guard",
        "nixe.cogs.link_phish_guard",
        "nixe.cogs.ban_commands",
    ]:
        try:
            await bot.load_extension(ext)
        except Exception as e:
            logging.getLogger("nixe").warning("load_extension %s failed: %s", ext, e)

@bot.event
async def on_ready():
    logging.getLogger("nixe").info("Bot ready as %s", bot.user)

async def run_bot():
    await _load_cogs()
    token = os.environ["DISCORD_TOKEN"]
    await bot.start(token)

async def run_web():
    port = int(os.getenv("PORT", "8000"))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    bot_task = asyncio.create_task(run_bot())
    web_task = asyncio.create_task(run_web())
    done, pending = await asyncio.wait({bot_task, web_task}, return_when=asyncio.FIRST_EXCEPTION)
    for t in pending: t.cancel()
    # If web server exits (Render stop/restart), close bot gracefully
    if bot_task in done and not bot.is_closed():
        await bot.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
