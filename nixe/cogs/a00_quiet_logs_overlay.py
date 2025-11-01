# nixe/cogs/a00_quiet_logs_overlay.py
import logging
from discord.ext import commands

TARGETS = [
    "nixe.cogs.a16_lpg_provider_enforcer_overlay",
    "nixe.helpers.attachment_mirror",
    "nixe.cogs.phash_db_board",
    "nixe.cogs.phash_db_thread_manager",
    "nixe.cogs.phash_rescanner",
    "nixe.cogs.suspicious_attachment_guard",
    "nixe.cogs.lucky_pull_auto",
]

class QuietLogsOverlay(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        for name in TARGETS:
            lg = logging.getLogger(name)
            lg.setLevel(logging.ERROR)
            lg.propagate = False  # keep it quiet

async def setup(bot: commands.Bot):
    await bot.add_cog(QuietLogsOverlay(bot))
