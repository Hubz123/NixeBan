from __future__ import annotations
import os, importlib, pkgutil, logging
from discord.ext import commands
log = logging.getLogger(__name__)
EXCLUDE = set(s.strip() for s in os.getenv("COG_EXCLUDE","").split(",") if s.strip())
def _discover(base: str = "nixe.cogs"):
    pkg = importlib.import_module(base)
    for mod in pkgutil.iter_modules(pkg.__path__, base + "."):
        name = mod.name
        if name in {__name__, base + ".__pycache__"}: continue
        yield name
class NixeCogsLoader(commands.Cog):
    def __init__(self, bot: commands.Bot): self.bot=bot; self._loaded_once=False
    def _try_load(self, ext: str):
        if ext in EXCLUDE: log.info("[loader] excluded: %s", ext); return
        try: self.bot.load_extension(ext); log.info("✅ Loaded cog: %s", ext)
        except commands.ExtensionAlreadyLoaded: log.debug("[loader] already loaded: %s", ext)
        except Exception as e: log.warning("[loader] failed: %s (%s)", ext, e)
    def _load_all(self): 
        for ext in _discover("nixe.cogs"): self._try_load(ext)
    @commands.Cog.listener()
    async def on_ready(self):
        if self._loaded_once: return
        self._loaded_once=True; self._load_all()
async def setup(bot: commands.Bot): await bot.add_cog(NixeCogsLoader(bot))
