# -*- coding: utf-8 -*-
from __future__ import annotations
import logging
from discord.ext import commands
from nixe.helpers.persona_loader import reload_persona
log = logging.getLogger(__name__)

class PersonaAdmin(commands.Cog):
    def __init__(self, bot: commands.Bot): self.bot = bot

    @commands.command(name='persona_reload', help='Reload persona JSON from disk. Usage: !persona_reload yandere')
    @commands.has_permissions(manage_guild=True)
    async def persona_reload(self, ctx: commands.Context, name: str = 'yandere'):
        try:
            reload_persona(name)
            await ctx.reply(f'✅ Persona "{name}" reloaded from disk.', mention_author=False)
        except Exception as e:
            await ctx.reply(f'❌ Reload failed: {e}', mention_author=False)

async def setup(bot: commands.Bot):
    if bot.get_cog('PersonaAdmin'): return
    try:
        await bot.add_cog(PersonaAdmin(bot))
    except Exception:
        pass
