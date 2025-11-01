# nixe/cogs/a00_quiet_logs_early_overlay.py
import logging
from discord.ext import commands
TARGETS=[
 "nixe.cogs.phash_hourly_scheduler","nixe.cogs.a16_lpg_provider_enforcer_overlay","nixe.helpers.attachment_mirror",
 "nixe.cogs.suspicious_attachment_guard","nixe.cogs.phash_imagephising_inbox_watcher","nixe.cogs.phash_rescanner",
 "nixe.cogs.phash_db_thread_manager","nixe.cogs.phash_db_board","nixe.cogs.lucky_pull_auto","nixe.helpers.lpa_provider_bridge"]
def _apply():
    for n in TARGETS:
        lg=logging.getLogger(n); lg.setLevel(logging.ERROR); lg.propagate=False
class QuietLogsEarly(commands.Cog):
    def __init__(self,bot): self.bot=bot
async def setup(bot: commands.Bot):
    _apply(); await bot.add_cog(QuietLogsEarly(bot))
