# nixe/cogs/a16_lpg_provider_enforcer_overlay.py — fix "was never awaited"
import os
from discord.ext import commands

class LPGProviderEnforcer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # No heavy work here; other overlays can read ENV to enforce behavior.

async def setup(bot: commands.Bot):
    # Correct: await add_cog (async) to avoid RuntimeWarning
    await bot.add_cog(LPGProviderEnforcer(bot))
