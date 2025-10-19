
import os, logging, asyncio, time
import discord
from discord.ext import commands
from dotenv import load_dotenv

from nixe.config import load as load_cfg

load_dotenv()
cfg = load_cfg()

logging.basicConfig(
    level=getattr(logging, cfg.log_level, logging.INFO),
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s"
)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
START_TS = time.time()

@bot.event
async def on_ready():
    logging.getLogger("nixe").info("Nixe ready as %s (%s)", bot.user, bot.user.id)
    try:
        synced = await bot.tree.sync()
        logging.getLogger("nixe").info("App commands synced: %d", len(synced))
    except Exception as e:
        logging.getLogger("nixe").warning("Slash sync skipped: %s", e)

async def start_http_server():
    # Minimal aiohttp app for health checks
    from aiohttp import web
    routes = web.RouteTableDef()

    @routes.get("/healthz")
    async def healthz(request):
        strict = os.getenv("STRICT_HEALTH","0").strip().lower() in ("1","true","yes","on","y")
        ready_after = int(os.getenv("HEALTH_READY_AFTER_SECONDS","30"))
        uptime = int(time.time() - START_TS)
        is_ready = bot.is_ready() and uptime >= ready_after
        status = 200 if (is_ready or not strict) else 503

        if request.query.get("full") == "1":
            # Try to surface internal state
            cog = bot.get_cog("ImagePhishGuard")
            entries = 0
            loaded_from = ""
            try:
                if cog and hasattr(cog, "db"):
                    entries = len(cog.db)
                    loaded_from = getattr(cog.db, "loaded_from", "")
            except Exception:
                pass
            data = {
                "ok": (is_ready or not strict),
                "ready": is_ready,
                "uptime_s": uptime,
                "guilds": len(bot.guilds),
                "image_db_entries": int(entries),
                "image_db_from": loaded_from,
            }
            return web.json_response(data, status=status)

        return web.Response(text=("ok" if (is_ready or not strict) else "starting"), status=status)

    @routes.get("/readyz")
    async def readyz(request):
        ready_after = int(os.getenv("HEALTH_READY_AFTER_SECONDS","30"))
        uptime = int(time.time() - START_TS)
        if not (bot.is_ready() and uptime >= ready_after):
            return web.Response(text="not ready", status=503)
        # Also require image DB to be loaded (entries > 0)
        cog = bot.get_cog("ImagePhishGuard")
        try:
            entries = len(cog.db) if cog and hasattr(cog, "db") else 0
        except Exception:
            entries = 0
        if entries <= 0:
            return web.Response(text="db empty", status=503)
        return web.Response(text="ready", status=200)

    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.getLogger("nixe").info("Health server started on 0.0.0.0:%d", port)

async def main():
    async with bot:
        # Load cogs
        for ext in [
            "nixe.cogs.image_phish_guard",
            "nixe.cogs.link_phish_guard",
        ]:
            try:
                await bot.load_extension(ext)
                logging.getLogger("nixe").info("Loaded %s", ext)
            except Exception as e:
                logging.getLogger("nixe").exception("Load failed for %s: %s", ext, e)

        # Start health server (Render Web will hit $PORT)
        asyncio.create_task(start_http_server())

        if not cfg.token:
            raise SystemExit("BOT_TOKEN is empty. Set it in environment or .env")
        await bot.start(cfg.token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
