
import os
import logging
from discord.ext import commands

log = logging.getLogger(__name__)

ENABLE = os.getenv("PHASH_FIRST_TOUCHDOWN", "1") == "1"

class pHashFirstTouchdownEnforcer(commands.Cog):
    """
    Ensures pHash anti-phishing is armed at startup and strict in first-contact.
    This overlay does not reimplement pHash matching; it enforces config/env so
    the existing pHash cogs (db manager/board/scheduler) run with safe defaults.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not ENABLE:
            log.info("[phash-first] disabled")
            return
        # Defaults that are safe for first ban touchdown
        defaults = {
            "PHASH_MATCH_THRESHOLD": os.getenv("PHASH_MATCH_THRESHOLD", "0.92"),
            "PHISH_DELETE_ON_MATCH": os.getenv("PHISH_DELETE_ON_MATCH", "1"),
            "PHISH_BAN_ON_MATCH": os.getenv("PHISH_BAN_ON_MATCH", "1"),
            "PHASH_STRICT_EDIT": os.getenv("PHASH_STRICT_EDIT", "1"),
            "PHASH_DB_THREAD_ID": os.getenv("PHASH_DB_THREAD_ID", "1430048839556927589"),
            "PHASH_IMAGEPHISH_THREAD_ID": os.getenv("PHASH_IMAGEPHISH_THREAD_ID", "1409949797313679492"),
        }
        # Log effective values (other modules will read env via your hybrid loader)
        log.warning("[phash-first] armed: thr=%s delete=%s ban=%s strict_edit=%s db_thread=%s img_thread=%s",
            defaults["PHASH_MATCH_THRESHOLD"],
            defaults["PHISH_DELETE_ON_MATCH"],
            defaults["PHISH_BAN_ON_MATCH"],
            defaults["PHASH_STRICT_EDIT"],
            defaults["PHASH_DB_THREAD_ID"],
            defaults["PHASH_IMAGEPHISH_THREAD_ID"],
        )

async def setup(bot):
    if ENABLE:
        await bot.add_cog(pHashFirstTouchdownEnforcer(bot))
