
from __future__ import annotations
import os, importlib, pkgutil, logging
from discord.ext import commands
from nixe.helpers.bootstate import mark_cogs_loaded

log = logging.getLogger("nixe.cogs_loader")
EXCLUDE = set(s.strip() for s in os.getenv("COG_EXCLUDE", "").split(",") if s.strip())

def _discover_all(base: str = "nixe.cogs"):
    pkg = importlib.import_module(base)
    return [m.name for m in pkgutil.iter_modules(pkg.__path__, base + ".")]

def _discover(base: str = "nixe.cogs"):
    for name in _discover_all(base):
        mod = name.rsplit(".", 1)[-1]
        if mod.startswith("_"):
            continue
        if "cogs_loader" in name:
            # internal skip: never attempt to load loader modules themselves
            continue
        if name in EXCLUDE or mod in EXCLUDE:
            log.info("[loader] excluded by COG_EXCLUDE: %s", name)
            continue
        yield name

class NixeCogsLoader(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._loaded_once = False

    async def _try_load(self, ext: str) -> None:
        try:
            await self.bot.load_extension(ext)
            log.info("✅ Loaded cog: %s", ext)
        except commands.ExtensionAlreadyLoaded:
            log.info("✅ Loaded cog: %s", ext)
        except Exception as e:
            log.error("Failed to load %s: %s", ext, e, exc_info=True)

    async def _load_all(self) -> None:
        for ext in _discover("nixe.cogs"):
            await self._try_load(ext)
        # signal "cogs loaded" AFTER auto-discovery completes
        mark_cogs_loaded()

    @commands.Cog.listener()
    async def on_ready(self):
        if self._loaded_once:
            return
        self._loaded_once = True
        await self._load_all()

async def setup(bot: commands.Bot):
    await bot.add_cog(NixeCogsLoader(bot))
