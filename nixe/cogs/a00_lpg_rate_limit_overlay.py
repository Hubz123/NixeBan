# -*- coding: utf-8 -*-
"""
a00_lpg_rate_limit_overlay
- Provide sane defaults for Gemini Lucky Pull budgets so free plan won't rate-limit.
- No effect on phishing (Gemini already disabled by your block overlay).
"""
import os
from discord.ext import commands

class LpgRateLimitOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        os.environ.setdefault("LPG_GEMINI_ENABLE", "1")
        os.environ.setdefault("GEMINI_LUCKY_THRESHOLD", "0.77")
        os.environ.setdefault("LPG_GEM_MAX_RPM", "6")
        os.environ.setdefault("LPG_GEM_MAX_CONCURRENCY", "1")
        os.environ.setdefault("LPG_GEM_COOLDOWN_SEC", "2")
        os.environ.setdefault("LPG_GEM_RETRY_ON_429", "1")
        os.environ.setdefault("LPG_GEM_BACKOFF_MS", "8000")
        os.environ.setdefault("LPG_GEM_CACHE_TTL_SEC", "600")
        os.environ.setdefault("LPG_ONLY_IF_HEUR_SCORE_GE", "0.50")
async def setup(bot):
    await bot.add_cog(LpgRateLimitOverlay(bot))