from __future__ import annotations
import discord
from discord.ext import commands

class BanCommandsFix(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="banfix")
    @commands.has_permissions(ban_members=True)
    async def banfix(self, ctx: commands.Context, user: discord.User, *, reason: str = "banfix"):
        try:
            await ctx.guild.ban(user, reason=reason)
            await ctx.reply(f"✅ Banned {user} (fallback).")
        except Exception as e:
            await ctx.reply(f"❌ Ban failed: {e}")

    @commands.command(name="unbanfix")
    @commands.has_permissions(ban_members=True)
    async def unbanfix(self, ctx: commands.Context, user_id: int):
        try:
            await ctx.guild.unban(discord.Object(id=user_id))
            await ctx.reply(f"✅ Unbanned {user_id} (fallback).")
        except Exception as e:
            await ctx.reply(f"❌ Unban failed: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(BanCommandsFix(bot))
