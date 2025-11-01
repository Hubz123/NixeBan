# nixe/cogs/a00_quiet_logs_overlay.py (reduce noise to ERROR on_ready)
import logging
from discord.ext import commands

TARGETS = [
    "nixe.cogs.suspicious_attachment_guard",
    "nixe.cogs.a00_phash_db_edit_fix_overlay",
    "nixe.cogs.phash_hourly_scheduler",
    "nixe.cogs.lucky_pull_auto",
    "nixe.cogs.phash_db_board",
]

class QuietLogsOverlay(commands.Cog):
    def __init__(self, bot): self.bot=bot

    @commands.Cog.listener()
    async def on_ready(self):
        for name in TARGETS:
            lg = logging.getLogger(name)
            lg.setLevel(logging.ERROR)
            lg.propagate = False  # don't bubble up

async def setup(bot: commands.Bot):
    await bot.add_cog(QuietLogsOverlay(bot))
