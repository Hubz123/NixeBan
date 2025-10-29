
from __future__ import annotations
import asyncio
from typing import List
from discord.ext import commands

LEGACY_EXTS: List[str] = [
    "nixe.cogs.gacha_luck_guard",
    "nixe.cogs.gacha_luck_guard_random_only",
    "nixe.cogs.lucky_pull_auto",
]

TARGET_NEW = "nixe.cogs.lucky_pull_guard"

class BlockLegacyGachaGuardsPlus(commands.Cog):
    """Enforce only lucky_pull_guard stays; retry for a short window after ready
    to catch late loaders from dynamic loaders."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._enforce_task = asyncio.create_task(self._enforce_loop())

    async def _enforce_once(self):
        exts = set(self.bot.extensions.keys())
        if TARGET_NEW not in exts:
            return False
        changed = False
        for name in list(LEGACY_EXTS):
            if name in exts:
                try:
                    await self.bot.unload_extension(name)
                    try:
                        self.bot.logger.warning("[legacy-guard-block+:enforce] unloaded extension: %s", name)
                    except Exception:
                        pass
                    changed = True
                except Exception as e:
                    try:
                        self.bot.logger.warning("[legacy-guard-block+:enforce] failed to unload %s: %r", name, e)
                    except Exception:
                        pass
        return changed

    async def _enforce_loop(self):
        # Retry up to ~15s (15 attempts) after bot starts
        for _ in range(15):
            try:
                await asyncio.sleep(1.0)
                await self._enforce_once()
            except Exception:
                # never crash the bot
                pass

    @commands.Cog.listener()
    async def on_connect(self):
        await self._enforce_once()

    @commands.Cog.listener()
    async def on_ready(self):
        # one more immediate pass
        await self._enforce_once()

async def setup(bot: commands.Bot):
    await bot.add_cog(BlockLegacyGachaGuardsPlus(bot))
