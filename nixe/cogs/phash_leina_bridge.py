from __future__ import annotations
import logging
from discord.ext import commands
log = logging.getLogger("nixe.cogs.phash_leina_bridge")

class PHashLeinaBridge(commands.Cog):
    """Stub bridge for NIXE (disabled). Keeps loader happy and avoids NameError."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(PHashLeinaBridge(bot))

def setup_legacy(bot: commands.Bot):
    bot.add_cog(PHashLeinaBridge(bot))
