from __future__ import annotations
import os, importlib, pkgutil, logging, inspect
from discord.ext import commands

log = logging.getLogger(__name__)
EXCLUDE = set(s.strip() for s in os.getenv("COG_EXCLUDE", "").split(",") if s.strip())

def _discover_all(base: str = "nixe.cogs"):
    pkg = importlib.import_module(base)
    return [m.name for m in pkgutil.iter_modules(pkg.__path__, base + ".")]

class NixeCogsLoader(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._loaded_once = False

    async def _try_load(self, ext: str) -> None:
        if ext in EXCLUDE:
            log.info("[loader] excluded by COG_EXCLUDE: %s", ext); return
        try:
            ret = self.bot.load_extension(ext)
            if inspect.isawaitable(ret):
                await ret
            log.info("✅ Loaded cog: %s", ext)
        except commands.ExtensionAlreadyLoaded:
            log.debug("[loader] already loaded: %s", ext)
        except Exception as e:
            # Keep calm & boot — many cogs may already be loaded by specific *_loader files
            log.warning("[loader] failed: %s (%s)", ext, e, exc_info=True)

    async def _load_all(self) -> None:
        exts = _discover_all("nixe.cogs")
        # Load *loader* modules first
        loaders = [e for e in exts if e.rsplit(".",1)[-1].endswith("_loader")]
        others  = [e for e in exts if e not in loaders]
        # If a loader exists for a stem, skip the base module with the same stem
        loader_stems = {e.rsplit(".",1)[-1].replace("_loader","") for e in loaders}
        others = [e for e in others if e.rsplit(".",1)[-1] not in loader_stems]
        for e in loaders + others:
            await self._try_load(e)

    @commands.Cog.listener()
    async def on_ready(self):
        if self._loaded_once:
            return
        self._loaded_once = True
        await self._load_all()

async def setup(bot: commands.Bot):
    await bot.add_cog(NixeCogsLoader(bot))
