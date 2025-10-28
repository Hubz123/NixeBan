# -*- coding: utf-8 -*-
from __future__ import annotations
from discord.ext import commands
from nixe.cogs.lucky_pull_guard import LuckyPullGuard

class LuckyPullGuard_Loader(commands.Cog):
    def __init__(self, bot): self.bot = bot

async def setup(bot):
    if bot.get_cog("LuckyPullGuard") or bot.get_cog("LuckyPullDeleteMentionEnforcer"):
        return  # already loaded
    try:
        await bot.add_cog(LuckyPullGuard(bot))
    except Exception:
        pass
