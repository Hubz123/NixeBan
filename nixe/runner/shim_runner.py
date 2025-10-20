from __future__ import annotations
import os, logging, discord
from discord.ext import commands

# Load (and apply) ban dedupe patch early
try:
    from ..patches import ban_dedupe  # noqa: F401
except Exception:
    pass

log = logging.getLogger(__name__)

# ===== Intents =====
intents = discord.Intents.default()
intents.guilds = True
intents.members = os.getenv("INTENTS_MEMBERS", "0") in ("1","true","TRUE")
intents.presences = os.getenv("INTENTS_PRESENCES", "0") in ("1","true","TRUE")
intents.message_content = True  # ensure enabled on portal

PREFIX = os.getenv("COMMAND_PREFIX", "!")
allowed_mentions = discord.AllowedMentions(
    everyone=False, users=True, roles=False, replied_user=False
)
bot = commands.Bot(command_prefix=PREFIX, intents=intents, allowed_mentions=allowed_mentions)

@bot.event
async def setup_hook():
    # Auto-load all cogs using Leina-style loader
    try:
        await bot.load_extension("nixe.cogs.loader_leina")
    except Exception as e:
        log.error("Failed to load Nixe loader: %s", e, exc_info=True)

@bot.event
async def on_ready():
    try:
        log.info("✅ Bot login as %s (%s)", bot.user, bot.user.id if bot.user else "?")
    except Exception:
        log.info("✅ Bot login.")

async def start_bot():
    token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("ENV DISCORD_TOKEN / BOT_TOKEN not set")
    await bot.start(token)