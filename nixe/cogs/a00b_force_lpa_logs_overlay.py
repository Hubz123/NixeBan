# nixe/cogs/a00b_force_lpa_logs_overlay.py
# Purpose: Make sure Lucky Pull logs always appear:
#   INFO:nixe.cogs.lucky_pull_auto:[lpa] classify: ...
# without touching runtime_env.json.
import logging
from discord.ext import commands

class LPAForceLogsOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Ensure root has a handler and INFO level
        root = logging.getLogger()
        if not root.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
            root.addHandler(h)
        if root.level > logging.INFO:
            root.setLevel(logging.INFO)

        # Force our cog logger to INFO
        lpa = logging.getLogger("nixe.cogs.lucky_pull_auto")
        lpa.setLevel(logging.INFO)
        lpa.propagate = True

        # Optional: show one line so you can see overlay is active
        lpa.info("[lpa-log] force=INFO (overlay active)")

async def setup(bot: commands.Bot):
    await bot.add_cog(LPAForceLogsOverlay(bot))
