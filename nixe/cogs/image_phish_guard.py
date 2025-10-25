import os
from discord.ext import commands
SILENT = os.getenv("NIXE_LOG_PHISH_OBSERVED","0")=="0"
class _G(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @commands.Cog.listener()
    async def on_message(self,message): return
async def setup(bot): await bot.add_cog(_G(bot))
def legacy_setup(bot): bot.add_cog(_G(bot))
