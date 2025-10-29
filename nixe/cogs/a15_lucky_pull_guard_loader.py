# -*- coding: utf-8 -*-
from __future__ import annotations
import logging
from discord.ext import commands
log = logging.getLogger(__name__)

class LuckyPullGuard_Loader(commands.Cog):
    def __init__(self, bot): self.bot = bot

async def setup(bot: commands.Bot):
    # Lazy import to avoid crashing loader when guard has optional deps
    if bot.get_cog("LuckyPullGuard") or bot.get_cog("LuckyPullDeleteMentionEnforcer"):
        return
    try:
        from nixe.cogs.lucky_pull_guard import LuckyPullGuard  # import here
    except Exception as e:
        log.error("[lpg-loader] failed to import LuckyPullGuard: %s", e)
        return
    try:
        await bot.add_cog(LuckyPullGuard(bot))
    except Exception as e:
        log.error("[lpg-loader] add_cog failed: %s", e)
