# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from discord.ext import commands
from satpambot.bot.modules.discord_bot.config.self_learning_cfg import PHASH_LOG_SCAN_LIMIT

log = logging.getLogger(__name__)

class PatchCollectPhashWrapper(commands.Cog):
    def __init__(self, bot): self.bot=bot

    async def cog_load(self):
        try:
            import satpambot.ml.phash_reconcile as M
        except Exception as e:
            log.warning("[patch_collect_phash] cannot import phash_reconcile: %s", e); return
        if not hasattr(M, "collect_phash_from_log"):
            log.warning("[patch_collect_phash] function not found"); return

        orig = M.collect_phash_from_log
        async def wrapped(channel, limit_msgs=400, *a, **kw):
            limit = min(PHASH_LOG_SCAN_LIMIT, limit_msgs)
            log.info("[patch_collect_phash] limit=%s (orig=%s)", limit, limit_msgs)
            return await orig(channel, limit_msgs=limit, *a, **kw)

        M.collect_phash_from_log = wrapped  # type: ignore
        log.info("[patch_collect_phash] installed wrapper; limit=%s", PHASH_LOG_SCAN_LIMIT)

async def setup(bot): await bot.add_cog(PatchCollectPhashWrapper(bot))
