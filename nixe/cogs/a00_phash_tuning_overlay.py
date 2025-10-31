# -*- coding: utf-8 -*-
import os
from discord.ext import commands
class PhashTuningOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        os.environ.setdefault("PHASH_MATCH_DELETE_THRESHOLD", "0.92")
        os.environ.setdefault("PHASH_AUTOBAN_THRESHOLD", "0.96")
        os.environ.setdefault("PHASH_MATCH_DELETE_MAX_BITS", "12")
        os.environ.setdefault("PHASH_MATCH_LOG_TOPK", "6")
        os.environ.setdefault("PHASH_MATCH_DEBUG", "1")
        os.environ.setdefault("PHASH_RESCANNER_ENABLE", "1")
        os.environ.setdefault("PHASH_RESYNC_ON_BOOT", "1")
        os.environ.setdefault("PHASH_AUTORESEED_ENABLE", "1")
async def setup(bot):
    await bot.add_cog(PhashTuningOverlay(bot))