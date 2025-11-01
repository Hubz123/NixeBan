# nixe/cogs/a00zz_force_lpa_logs_overlay.py
import logging, asyncio
from discord.ext import commands

TARGET_LOGGERS = [
    "nixe.cogs.lucky_pull_auto",
    "nixe.cogs.luckypull_guard",
]

def _ensure():
    root = logging.getLogger()
    if not root.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
        root.addHandler(h)
    if root.level > logging.INFO:
        root.setLevel(logging.INFO)
    for name in TARGET_LOGGERS:
        lg = logging.getLogger(name)
        lg.setLevel(logging.INFO)
        lg.propagate = True

class LPAForceLogsOverlay2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        _ensure()
        logging.getLogger("nixe.cogs.lucky_pull_auto").info("[lpa-log] force=INFO (overlay v2 active)")

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(1.0)
        _ensure()
        logging.getLogger("nixe.cogs.lucky_pull_auto").info("[lpa-log] re-assert INFO after ready")

async def setup(bot):
    await bot.add_cog(LPAForceLogsOverlay2(bot))
