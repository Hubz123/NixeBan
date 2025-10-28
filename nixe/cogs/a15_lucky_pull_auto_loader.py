# -*- coding: utf-8 -*-
from __future__ import annotations

async def setup(bot):
    try:
        if bot.get_cog("LuckyPullAuto"):
            return
    except Exception:
        pass
    try:
        await bot.load_extension("nixe.cogs.lucky_pull_auto")
    except Exception:
        # If extension not present or already loaded, ignore.
        pass
