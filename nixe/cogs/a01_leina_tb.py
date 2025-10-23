from __future__ import annotations
from typing import Optional
import discord
from discord.ext import commands
from ..config_ids import TESTBAN_CHANNEL_ID
from .ban_embed_leina import build_testban_embed

class LeinaTB(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="tb", aliases=["TB"], help="Test Ban (Simulasi) — format LEINA.")
    @commands.guild_only()
    async def tb(self, ctx: commands.Context, member: Optional[discord.Member]=None, *, reason: str="—"):
        if member is None and ctx.message.reference:
            try:
                ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                if isinstance(ref_msg.author, discord.Member):
                    member = ref_msg.author
            except Exception:
                pass
        if member is None:
            await ctx.reply("❌ Target tidak ditemukan. Mention user atau balas (reply) pesannya.", mention_author=False)
            return

        evidence = None
        try:
            if ctx.message.attachments:
                evidence = ctx.message.attachments[0].url
            elif ctx.message.embeds:
                e = ctx.message.embeds[0]
                url = None
                if getattr(e, "image", None) and getattr(e.image, "url", None): url = e.image.url
                elif getattr(e, "thumbnail", None) and getattr(e.thumbnail, "url", None): url = e.thumbnail.url
                evidence = url
        except Exception:
            evidence = None

        embed = build_testban_embed(target=member, moderator=ctx.author, reason=reason, evidence_url=evidence)

        # Send to TESTBAN channel
        try:
            ch = ctx.guild.get_channel(TESTBAN_CHANNEL_ID) or await self.bot.fetch_channel(TESTBAN_CHANNEL_ID)
            if ch and isinstance(ch, (discord.TextChannel, discord.Thread)):
                await ch.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            pass

        try:
            await ctx.message.add_reaction("✅")
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(LeinaTB(bot))

def setup_legacy(bot: commands.Bot):
    bot.add_cog(LeinaTB(bot))
