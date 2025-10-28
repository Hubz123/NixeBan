from __future__ import annotations
import logging
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

ALLOW = {
    "nixe.cogs.lucky_pull_guard",          # our unified guard
    "nixe.cogs.lucky_pull_auto",           # harmless stub
    "nixe.cogs.a15_lucky_pull_guard_loader",
    "nixe.cogs.a15_lucky_pull_auto_loader",
}

PATTERN_PREFIXES = ("nixe.cogs.lucky", "nixe.cogs.gacha")

def _is_guard_like(name: str) -> bool:
    return any(name.startswith(p) for p in PATTERN_PREFIXES)

class BlockLegacyGachaGuards(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._sweeps = 0
        self._sweeper.change_interval(seconds=10.0)
        self._sweeper.start()

    async def _purge(self, reason: str):
        for name in list(self.bot.extensions.keys()):
            if _is_guard_like(name) and name not in ALLOW:
                try:
                    await self.bot.unload_extension(name)
                    log.warning("[legacy-guard-block:%s] unloaded extension: %s", reason, name)
                except Exception as e:
                    log.warning("[legacy-guard-block:%s] failed to unload %s: %s", reason, name, e)

    @tasks.loop(seconds=25.0, count=6)
    async def _sweeper(self):
        self._sweeps += 1
        await self._purge(f"sweep#{self._sweeps}")

    @_sweeper.before_loop
    async def _before(self):
        try:
            await self.bot.wait_until_ready()
        except Exception:
            pass

    @commands.Cog.listener("on_connect")
    async def _on_connect(self):
        await self._purge("connect")

    @commands.Cog.listener("on_ready")
    async def _on_ready(self):
        await self._purge("ready")

async def setup(bot: commands.Bot):
    await bot.add_cog(BlockLegacyGachaGuards(bot))
