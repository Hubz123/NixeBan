# -*- coding: utf-8 -*-

async def setup(bot):
    try:
        if bot.get_cog("LuckyPullAuto"):
            return
    except Exception:
        pass
    try:
        await bot.load_extension("nixe.cogs.lucky_pull_auto")
    except Exception:
        pass
