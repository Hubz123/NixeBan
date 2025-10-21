
# -*- coding: utf-8 -*-
from __future__ import annotations
from discord.ext import commands
async def setup(bot: commands.Bot):
    from .lucky_pull_auto import LuckyPullAuto
    await bot.add_cog(LuckyPullAuto(bot))
