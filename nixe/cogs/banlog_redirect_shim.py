import os, logging
from discord.ext import commands
log=logging.getLogger(__name__)
BLOCKED=int(os.getenv('LOG_CHANNEL_ID','0') or 0)
async def nixe_get(guild):
    pref=int(os.getenv('NIXE_BAN_LOG_CHANNEL_ID', os.getenv('LOG_CHANNEL_ID','0')) or 0)
    if pref:
        try:
            ch=guild.get_channel(pref) or await guild.fetch_channel(pref)
            if ch and getattr(ch,'id',0)!=BLOCKED: return ch
        except Exception: pass
    name=(os.getenv('MOD_LOG_CHANNEL_NAME','nixe-only') or 'nixe-only').lower()
    for c in guild.text_channels:
        if (c.name or '').lower()==name and c.id!=BLOCKED: return c
    return None
async def nixe_ensure(ch):
    if not ch or getattr(ch,'id',0)==BLOCKED: return None
    return ch
class Shim(commands.Cog):
    def __init__(self,bot): self.bot=bot
async def setup(bot): await bot.add_cog(Shim(bot))
def legacy_setup(bot): bot.add_cog(Shim(bot))
