# -*- coding: utf-8 -*-
import os, logging
from discord.ext import commands
log = logging.getLogger("nixe.cogs.a00_block_gemini_phish_overlay")
class BlockGeminiPhishOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        os.environ.setdefault("PHISH_GEMINI_ENABLE", "0")
        os.environ.setdefault("IMAGE_PHISH_GEMINI_ENABLE", "0")
        os.environ.setdefault("SUS_ATTACH_USE_GEMINI", "0")
        os.environ.setdefault("SUS_ATTACH_ALWAYS_GEM", "0")
        os.environ.setdefault("SUS_ATTACH_GEMINI_THRESHOLD", "9.99")
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            self.bot.unload_extension("nixe.cogs.image_phish_gemini_guard")
            log.warning("[gemini-phish:block] unloaded extension: nixe.cogs.image_phish_gemini_guard")
        except Exception as e:
            log.info("[gemini-phish:block] guard not loaded or already removed: %r", e)
async def setup(bot):
    await bot.add_cog(BlockGeminiPhishOverlay(bot))