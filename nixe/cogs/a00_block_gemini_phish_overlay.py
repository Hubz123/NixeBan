# nixe/cogs/a00_block_gemini_phish_overlay.py
# Drop-in fix: correctly await unload_extension (supports async or sync), silent.
import inspect
from discord.ext import commands

TARGET_EXT = "nixe.cogs.image_phish_gemini_guard"

class BlockGeminiPhishOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _safe_unload(self, name: str):
        try:
            # Skip if not loaded
            if name not in getattr(self.bot, "extensions", {}):
                return
            fn = getattr(self.bot, "unload_extension", None)
            if not fn:
                return
            # Call and await if needed (covers async/sync implementations)
            result = fn(name)
            if inspect.isawaitable(result):
                await result
        except Exception:
            # stay silent
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        await self._safe_unload(TARGET_EXT)

async def setup(bot: commands.Bot):
    await bot.add_cog(BlockGeminiPhishOverlay(bot))
