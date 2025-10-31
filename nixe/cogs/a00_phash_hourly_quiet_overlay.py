# nixe/cogs/a00_phash_hourly_quiet_overlay.py
import os, re, logging
from discord.ext import commands

def _env_bool(name: str, default: bool=False) -> bool:
    val = os.getenv(name, None)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on", "y")

class PhashHourlyQuietOverlay(commands.Cog):
    """Mute 'collected phash: ~0 entries' spam from phash_hourly_scheduler."""
    def __init__(self, bot):
        self.bot = bot
        self._install_filter()

    def _install_filter(self):
        # Only install if user doesn't want zero-logs
        if not _env_bool("PHASH_HOURLY_LOG_WHEN_ZERO", False):
            logger = logging.getLogger("nixe.cogs.phash_hourly_scheduler")
            class _ZeroOnlyFilter(logging.Filter):
                def filter(self, record: logging.LogRecord) -> bool:
                    msg = record.getMessage()
                    # Drop lines like: "collected phash: ~0 entries"
                    return not re.search(r"collected phash:\s*~?0\s+entries\b", msg)
            logger.addFilter(_ZeroOnlyFilter())
            logging.getLogger(__name__).warning("[phash-hourly-quiet] zero-entry logs suppressed (set PHASH_HOURLY_LOG_WHEN_ZERO=1 to re-enable)")

async def setup(bot):
    await bot.add_cog(PhashHourlyQuietOverlay(bot))
