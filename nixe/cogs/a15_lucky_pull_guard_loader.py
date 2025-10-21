
# -*- coding: utf-8 -*-
from __future__ import annotations
from discord.ext import commands

async def setup(bot: commands.Bot):
    from .lucky_pull_guard import LuckyPullGuard
    await bot.add_cog(LuckyPullGuard(bot))
