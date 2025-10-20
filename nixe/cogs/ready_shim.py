from __future__ import annotations
import asyncio, logging
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

class ReadyShim(commands.Cog):
    """Leina-style 'ready' shim.
    - Guarantees on_ready is logged **once**
    - Exposes `wait_until_ready_once()` for other cogs that need a late start
    - Useful on platforms like Render where connect/resume may happen multiple times
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ready_once = asyncio.Event()

    async def wait_until_ready_once(self):
        """Await this in other cogs to defer work until the first on_ready fired."""
        await self._ready_once.wait()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._ready_once.is_set():
            self._ready_once.set()
            log.info("[ready] Bot ready as %s (%s)", self.bot.user, getattr(self.bot.user, "id", "?"))
        else:
            log.info("[ready] Resumed as %s", self.bot.user)

    @commands.Cog.listener()
    async def on_connect(self):
        log.debug("[ready] Connected to gateway")

    @commands.Cog.listener()
    async def on_resumed(self):
        log.debug("[ready] Session resumed")

async def setup(bot: commands.Bot):
    await bot.add_cog(ReadyShim(bot))
