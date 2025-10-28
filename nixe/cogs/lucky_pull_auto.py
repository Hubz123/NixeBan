# -*- coding: utf-8 -*-
from __future__ import annotations
from discord.ext import commands

class LuckyPullAuto(commands.Cog):
    def __init__(self, bot): self.bot = bot

async def setup(bot):
    if bot.get_cog("LuckyPullAuto"):
        return
    try:
        await bot.add_cog(LuckyPullAuto(bot))
    except Exception:
        pass
