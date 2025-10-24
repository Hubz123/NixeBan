# Auto-added: Hard enforcement so Nixe only uses #nixe-only + phash-db thread
import logging, os
from discord.ext import commands
from nixe import config
log = logging.getLogger(__name__)

NEW_LOG = 1431178130155896882
NEW_DB  = 1431192568221270108

class HardEnforceNixeOnly(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Force override config at runtime
        try:
            config.PHISH_LOG_CHAN_ID = NEW_LOG
        except Exception: pass
        try:
            config.LOG_CHANNEL_ID = NEW_LOG
        except Exception: pass
        try:
            config.PHASH_DB_THREAD_ID = NEW_DB
        except Exception: pass

        # Also fix environment for any lazy readers
        os.environ['NIXE_PHISH_LOG_CHAN_ID'] = str(NEW_LOG)
        os.environ['LOG_CHANNEL_ID'] = str(NEW_LOG)
        os.environ['NIXE_PHASH_DB_THREAD_ID'] = str(NEW_DB)
        log.warning("[nixe-only] Enforced LOG_CHANNEL_ID=%s PHASH_DB_THREAD_ID=%s", NEW_LOG, NEW_DB)

async def setup(bot):
    await bot.add_cog(HardEnforceNixeOnly(bot))
