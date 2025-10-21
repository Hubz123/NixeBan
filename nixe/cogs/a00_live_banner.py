
import asyncio
from discord.ext import commands

class LiveBanner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._done = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._done:
            return
        self._done = True
        await asyncio.sleep(0.5)
        print("==> Your service is live 🎉")  # bare print so it matches exactly (no logger prefix)

async def setup(bot: commands.Bot):
    await bot.add_cog(LiveBanner(bot))
