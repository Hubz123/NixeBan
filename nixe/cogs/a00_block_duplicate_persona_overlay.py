# nixe/cogs/a00_block_duplicate_persona_overlay.py
from discord.ext import commands
import logging, asyncio, inspect
_log = logging.getLogger(__name__)
TARGET_EXT = "nixe.cogs.a16_lpg_persona_react_overlay"

class BlockDuplicatePersona(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._done = False

    async def _try_unload(self):
        if self._done:
            return
        self._done = True
        try:
            if TARGET_EXT in self.bot.extensions:
                fn = getattr(self.bot, "unload_extension")
                res = fn(TARGET_EXT)
                if inspect.isawaitable(res):
                    await res
                _log.info(f"[persona-dedupe] unloaded ext: {TARGET_EXT}")
            else:
                _log.info(f"[persona-dedupe] ext not loaded (OK): {TARGET_EXT}")
        except Exception as e:
            _log.warning(f"[persona-dedupe] failed to unload {TARGET_EXT}: {e!r}")

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(0.3)
        await self._try_unload()

async def setup(bot: commands.Bot):
    add = getattr(bot, "add_cog")
    res = add(BlockDuplicatePersona(bot))
    if inspect.isawaitable(res):
        await res
