from __future__ import annotations
import contextlib
from typing import Optional
import discord
from discord.ext import commands
from ..config_ids import LOG_BOTPHISHING, TESTBAN_CHANNEL_ID
from .ban_embed_leina import build_testban_embed

def _can_send(ch: discord.abc.GuildChannel, me: discord.Member) -> bool:
    try:
        perms = ch.permissions_for(me)
        return perms.send_messages and perms.embed_links
    except Exception:
        return True

class BanCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="testban", aliases=["tb","TB"], help="Kirim embed Test Ban (Simulasi) gaya LEINA.")
    @commands.guild_only()
    async def testban(self, ctx: commands.Context, member: Optional[discord.Member]=None, *, reason: str="—"):
        # target: reply -> author; else mention; else invoker
        if member is None and ctx.message.reference:
            with contextlib.suppress(Exception):
                ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                if isinstance(ref_msg.author, discord.Member):
                    member = ref_msg.author
        if member is None:
            member = ctx.author

        # evidence: dari command message
        evidence = None
        with contextlib.suppress(Exception):
            if ctx.message.attachments:
                evidence = ctx.message.attachments[0].url
            elif ctx.message.embeds:
                e = ctx.message.embeds[0]
                url = None
                if getattr(e, "image", None) and getattr(e.image, "url", None): url = e.image.url
                elif getattr(e, "thumbnail", None) and getattr(e.thumbnail, "url", None): url = e.thumbnail.url
                evidence = url

        embed = build_testban_embed(target=member, moderator=ctx.author, reason=reason, evidence_url=evidence)

        # priority: TESTBAN channel -> LOG_BOTPHISHING -> current channel
        me = ctx.guild.me
        target_ch = None
        for cid in (TESTBAN_CHANNEL_ID, LOG_BOTPHISHING):
            if not cid: continue
            with contextlib.suppress(Exception):
                ch = ctx.guild.get_channel(cid) or await self.bot.fetch_channel(cid)
                if ch and isinstance(ch, (discord.TextChannel, discord.Thread)) and _can_send(ch, me):
                    target_ch = ch; break
        if target_ch is None:
            target_ch = ctx.channel

        try:
            await target_ch.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
            with contextlib.suppress(Exception): await ctx.message.add_reaction("✅")
        except discord.Forbidden:
            await ctx.reply("❌ Bot tidak punya izin kirim embed di channel tujuan.", mention_author=False)
        except Exception as e:
            await ctx.reply(f"❌ Gagal kirim embed: {e!r}", mention_author=False)

async def setup(bot: commands.Bot):
    # Safeguard: if another tb exists, we still register this cog but command name will be same;
    # discord.py will raise on conflict; so remove previous tb if it's just alias to old testban.
    if bot.get_command("tb") and bot.get_command("testban"):
        # Prefer this implementation: remove old command 'testban' then add ours.
        try:
            bot.remove_command("testban")
        except Exception:
            pass
    await bot.add_cog(BanCommands(bot))

def setup_legacy(bot: commands.Bot):
    try:
        if bot.get_command("tb") and bot.get_command("testban"):
            bot.remove_command("testban")
    except Exception:
        pass
    bot.add_cog(BanCommands(bot))
