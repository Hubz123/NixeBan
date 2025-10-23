from __future__ import annotations
import logging
from discord.ext import commands
log = logging.getLogger(__name__)
class _Noop(commands.Cog): pass
async def setup(bot: commands.Bot):
    log.info("noop tb shim loaded (disabled duplicate)")
    await bot.add_cog(_Noop(bot))
def setup_legacy(bot: commands.Bot):
    bot.add_cog(_Noop(bot))
