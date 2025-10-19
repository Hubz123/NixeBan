\
import logging, asyncio
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

@bot.event
async def on_ready():
    logging.getLogger("nixe").info("Nixe ready as %s (%s)", bot.user, bot.user.id)
    try:
        synced = await bot.tree.sync()
        logging.getLogger("nixe").info("App commands synced: %d", len(synced))
    except Exception as e:
        logging.getLogger("nixe").warning("Slash sync skipped: %s", e)

async def main():
    async with bot:
        for ext in ["nixe.cogs.image_phish_guard","nixe.cogs.link_phish_guard"]:
            try:
                await bot.load_extension(ext)
                logging.getLogger("nixe").info("Loaded %s", ext)
            except Exception as e:
                logging.getLogger("nixe").exception("Load failed for %s: %s", ext, e)
        if not cfg.token:
            raise SystemExit("BOT_TOKEN is empty. Set it in environment or .env")
        await bot.start(cfg.token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
