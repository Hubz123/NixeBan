# nixe/cogs/a00b_lpa_debug_log_override.py — raise lucky_pull_auto logger to INFO when LPA_DEBUG_LOG=1
import os, logging
from discord.ext import commands

class LpaDebugLogOverride(commands.Cog):
    def __init__(self, bot): self.bot=bot

async def setup(bot: commands.Bot):
    if os.getenv("LPA_DEBUG_LOG","0") == "1":
        lg = logging.getLogger("nixe.cogs.lucky_pull_auto")
        lg.setLevel(logging.INFO)
        lg.propagate = True  # let it through root handlers
    await bot.add_cog(LpaDebugLogOverride(bot))
