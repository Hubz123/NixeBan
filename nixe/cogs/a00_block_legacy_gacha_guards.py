from __future__ import annotations
import logging
from discord.ext import commands

log = logging.getLogger(__name__)

# Extensions/cogs yang harus dimatikan (karena masih pakai template lama)
LEGACY_EXTS = [
    "nixe.cogs.gacha_luck_guard",
    "nixe.cogs.gacha_luck_guard_v1",
    "nixe.cogs.gacha_guard",
    "nixe.cogs.gacha_redirect_guard",
    "nixe.cogs.lucky_pull_guard",
    "nixe.cogs.a15_lucky_pull_guard_loader",
    "nixe.cogs.a15_lucky_pull_auto_loader",
]

# Yang <= TETAP diizinkan (jangan di-unload)
ALLOWLIST = {
    "nixe.cogs.gacha_luck_guard_random_only",
}

class BlockLegacyGachaGuards(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _purge(self):
        # unload legacy guards (jika diload) dan cegah relaunch oleh loader lama
        to_unload = [m for m in LEGACY_EXTS if m in self.bot.extensions and m not in ALLOWLIST]
        for m in to_unload:
            try:
                await self.bot.unload_extension(m)
                log.warning("[legacy-guard-block] unloaded extension: %s", m)
            except Exception as e:
                log.warning("[legacy-guard-block] failed to unload %s: %s", m, e)

    @commands.Cog.listener("on_connect")
    async def _on_connect(self):
        await self._purge()

    @commands.Cog.listener("on_ready")
    async def _on_ready(self):
        # Purge lagi setelah ready untuk berjaga-jaga jika ada loader yang reload saat ready
        await self._purge()

async def setup(bot: commands.Bot):
    await bot.add_cog(BlockLegacyGachaGuards(bot))
