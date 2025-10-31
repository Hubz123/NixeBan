# nixe/cogs/a00_disable_gemini_warmup_overlay.py
import os, logging, asyncio
from discord.ext import commands

def _is_free_plan():
    return str(os.getenv("LPG_FREE_PLAN","0")).lower() in ("1","true","yes","on","y")

class DisableGeminiWarmup(commands.Cog):
    """Unload warmup on free plan to save quota."""
    def __init__(self, bot):
        self.bot = bot
        self.log = logging.getLogger(__name__)
        self.task = bot.loop.create_task(self._apply())

    async def _apply(self):
        await self.bot.wait_until_ready()
        if not _is_free_plan():
            self.log.info("[warmup-free] LPG_FREE_PLAN=0 -> keep warmup")
            return
        for ext in ("nixe.cogs.a16_gemini_warmup",):
            try:
                await self.bot.unload_extension(ext)
                self.log.warning("[warmup-free] unloaded: %s", ext)
            except Exception as e:
                self.log.info("[warmup-free] not loaded: %s (%s)", ext, e)

async def setup(bot):
    await bot.add_cog(DisableGeminiWarmup(bot))
