# -*- coding: utf-8 -*-
"""
Cog: PhashRuntimeLogTamer
- Meredam spam log dari modul pHash runtime dengan ENV `PHASH_RUNTIME_LOG_LEVEL`.
- Tidak menyentuh konfigurasi lain; aman untuk digabung.
"""
import os
import logging
from discord.ext import commands

class PhashRuntimeLogTamer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        level_name = os.getenv("PHASH_RUNTIME_LOG_LEVEL", "INFO").upper().strip()
        self.level = getattr(logging, level_name, logging.INFO)

    @commands.Cog.listener()
    async def on_ready(self):
        # Target umum
        candidates = [
            "satpambot.bot.modules.discord_bot.cogs.anti_image_phash_runtime",
            "anti_image_phash_runtime",
            "phash-runtime",
            "phash",
        ]
        root_mgr = logging.root.manager.loggerDict
        for name in list(root_mgr.keys()):
            if "phash" in name.lower():
                candidates.append(name)

        seen = set()
        for name in candidates:
            if not name or name in seen:
                continue
            seen.add(name)
            logger = logging.getLogger(name)
            logger.setLevel(self.level)

async def setup(bot):
    await bot.add_cog(PhashRuntimeLogTamer(bot))