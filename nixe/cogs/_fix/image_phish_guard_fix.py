from __future__ import annotations
from discord.ext import commands

class ImagePhishGuardFix(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(ImagePhishGuardFix(bot))
