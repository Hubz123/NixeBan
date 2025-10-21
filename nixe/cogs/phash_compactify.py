from __future__ import annotations
import logging
from discord.ext import commands
log = logging.getLogger(__name__)
class PhashCompactify(commands.Cog):
    """Stub pHash compactify cog (import-safe for smoke)."""
    def __init__(self, bot: commands.Bot): self.bot = bot
async def setup(bot: commands.Bot):
    await bot.add_cog(PhashCompactify(bot))
