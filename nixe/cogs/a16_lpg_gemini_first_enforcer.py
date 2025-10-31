# nixe/cogs/a16_lpg_gemini_first_enforcer.py
import os, logging, asyncio
from discord.ext import commands

def _set_default_env(name: str, value: str):
    if os.getenv(name) is None:
        os.environ[name] = value

class LPGGeminiFirstEnforcer(commands.Cog):
    """
    Enforce Gemini-first pipeline for Lucky Pull:
    - Ensure env flags for Gemini-only classification.
    - Set safe rate limits (rpm & concurrency).
    - Never delete on heuristics-only.
    """
    def __init__(self, bot):
        self.bot = bot
        self.log = logging.getLogger(__name__)
        self._task = bot.loop.create_task(self._apply())

    async def _apply(self):
        await self.bot.wait_until_ready()
        # Enforce Gemini-first
        _set_default_env("LPG_GEMINI_ENABLE", "1")
        _set_default_env("GEMINI_LUCKY_THRESHOLD", os.getenv("GEMINI_LUCKY_THRESHOLD", "0.85"))
        # Kill any fast/heuristic path (best-effort)
        _set_default_env("LPG_NO_FAST_HEURISTIC", "1")
        _set_default_env("LPA_REQUIRE_GEMINI", "1")
        _set_default_env("LPA_FAST_MODE", "0")
        _set_default_env("LPA_STRICT_MIN", "0.99")
        # Rate guard
        _set_default_env("LPG_GEM_MAX_RPM", os.getenv("LPG_GEM_MAX_RPM", "6"))
        _set_default_env("LPG_GEM_MAX_CONCURRENCY", os.getenv("LPG_GEM_MAX_CONCURRENCY", "1"))
        self.log.warning("[lpg-gemini-enforcer] Gemini-first enforced; fast heuristics disabled; rpm=%s conc=%s thr=%s",
                         os.getenv("LPG_GEM_MAX_RPM"), os.getenv("LPG_GEM_MAX_CONCURRENCY"), os.getenv("GEMINI_LUCKY_THRESHOLD"))

async def setup(bot):
    await bot.add_cog(LPGGeminiFirstEnforcer(bot))
