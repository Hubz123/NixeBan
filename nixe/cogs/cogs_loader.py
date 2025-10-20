from __future__ import annotations
import asyncio, logging, os
import importlib
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

# Default core cogs to load (can be overridden via env NIXE_AUTO_COGS CSV)
DEFAULT_COGS = [
    "nixe.cogs.ready_shim",          # ready signal first
    "nixe.cogs.phash_inbox_watcher", # pHash DB inbox watcher (no spam; edit-only)
    "nixe.cogs.image_phish_guard",   # pHash guard (simulate ban embed)
    "nixe.cogs.link_phish_guard",    # Link guard (simulate ban embed)
    "nixe.cogs.ban_commands",        # !testban/!tb and !ban
]

def _parse_env_list(name: str, fallback: list[str]) -> list[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return fallback
    return [x.strip() for x in raw.split(",") if x.strip()]

class NixeCogsLoader(commands.Cog):
    """Leina-style autoloader:
    - Loads configured cogs once **after** the client is ready
    - Ignores already-loaded extensions
    - Logs per-cog status for easier Render diagnostics
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cogs_to_load = _parse_env_list("NIXE_AUTO_COGS", DEFAULT_COGS)
        self._loaded_once = False

    async def _load_all(self):
        # ensure ready_shim is loaded first even if user removed it from env
        if "nixe.cogs.ready_shim" not in self.cogs_to_load:
            try:
                await self.bot.load_extension("nixe.cogs.ready_shim")
            except Exception as e:
                log.warning("[loader] ready_shim load failed: %s", e)
        for ext in self.cogs_to_load:
            if ext in getattr(self.bot, "extensions", {}):
                log.debug("[loader] already loaded: %s", ext)
                continue
            try:
                await self.bot.load_extension(ext)
                log.info("[loader] loaded: %s", ext)
            except commands.ExtensionAlreadyLoaded:
                log.debug("[loader] already loaded: %s", ext)
            except Exception as e:
                log.warning("[loader] failed: %s (%s)", ext, e)

    @commands.Cog.listener()
    async def on_ready(self):
        if self._loaded_once:
            return
        self._loaded_once = True
        await self._load_all()

async def setup(bot: commands.Bot):
    await bot.add_cog(NixeCogsLoader(bot))
