# nixe/cogs/ban_commands.py
from __future__ import annotations
import os, re, logging
from typing import Optional, Tuple
import discord
from discord.ext import commands

from .ban_embed import build_ban_embed
from ..helpers.banlog import get_ban_log_channel

log = logging.getLogger(__name__)

def _parse_args_for_user_and_reason(ctx: commands.Context, args: str) -> Tuple[Optional[discord.User], str]:
    # Simple parser: first token is mention/ID, rest is reason.
    user = None
    reason = ""
    if not args:
        return None, ""
    parts = args.split()
    if not parts:
        return None, ""
    target_raw = parts[0]
    rest = " ".join(parts[1:]) if len(parts) > 1 else ""

    m = re.fullmatch(r"<@!?(?P<i>\d+)>", target_raw)
    uid = None
    if m:
        uid = int(m.group("i"))
    else:
        try:
            uid = int(target_raw)
        except Exception:
            uid = None

    if uid:
        try:
            user = ctx.guild.get_member(uid) or ctx.bot.get_user(uid) or (await ctx.bot.fetch_user(uid))
        except Exception:
            try:
                user = await ctx.bot.fetch_user(uid)
            except Exception:
                user = None
    else:
        if ctx.message.mentions:
            user = ctx.message.mentions[0]
            rest = args
        else:
            user = None
            rest = args
    reason = (rest or "-").strip()
    return user, reason

class NixeBanCommands(commands.Cog):
    """!testban, !tb, dan !ban (NIXE config only)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.dry_default = os.getenv("BAN_DRY_RUN","0") == "1"
        self.delete_seconds = int(os.getenv("BAN_DELETE_SECONDS","0"))

    def _resolve_log(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        return get_ban_log_channel(guild)

    @commands.command(name="testban", aliases=["tb"])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def testban_cmd(self, ctx: commands.Context, *, args: str = ""):
        user, reason = await _maybe_await(_parse_args_for_user_and_reason, ctx, args)
        if not user:
            return await ctx.reply("Format: `!testban @user [alasan]`", mention_author=False)

        ch = self._resolve_log(ctx.guild)
        if not ch:
            return await ctx.reply("Log channel belum diset di NIXE. Set ENV `NIXE_BAN_LOG_CHANNEL_ID`.", mention_author=False)

        evidence_url = None
        if ctx.message.attachments:
            try:
                evidence_url = ctx.message.attachments[0].url
            except Exception:
                pass

        e = build_ban_embed(simulate=True, actor=ctx.author, target=user, reason=reason, evidence_url=evidence_url, source="manual")
        await ch.send(embed=e, allowed_mentions=discord.AllowedMentions.none())
        await ctx.message.add_reaction("✅")

    @commands.command(name="ban")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban_cmd(self, ctx: commands.Context, *, args: str = ""):
        user, reason = await _maybe_await(_parse_args_for_user_and_reason, ctx, args)
        if not user:
            return await ctx.reply("Format: `!ban @user [alasan]`", mention_author=False)

        dry = self.dry_default
        if re.search(r"\b--dry\b", reason):
            reason = re.sub(r"\s*--dry\b", "", reason).strip()
            dry = True

        ch = self._resolve_log(ctx.guild)
        if not ch:
            return await ctx.reply("Log channel belum diset di NIXE. Set ENV `NIXE_BAN_LOG_CHANNEL_ID`.", mention_author=False)

        evidence_url = None
        if ctx.message.attachments:
            try:
                evidence_url = ctx.message.attachments[0].url
            except Exception:
                pass

        e = build_ban_embed(simulate=dry, actor=ctx.author, target=user, reason=reason, evidence_url=evidence_url, source="manual")

        banned_ok = False
        if not dry:
            try:
                member = ctx.guild.get_member(user.id)
                await ctx.guild.ban(member or user, reason=reason, delete_message_seconds=self.delete_seconds)
                banned_ok = True
            except discord.Forbidden:
                await ctx.reply("Aku tidak punya izin ban untuk user ini.", mention_author=False)
            except Exception as exc:
                log.warning("Ban failed: %s", exc)
                await ctx.reply(f"Gagal ban: {exc}", mention_author=False)

        await ch.send(embed=e, allowed_mentions=discord.AllowedMentions.none())
        await ctx.message.add_reaction("✅" if (dry or banned_ok) else "⚠️")

async def _maybe_await(fn, *a, **kw):
    res = fn(*a, **kw)
    if hasattr(res, "__await__"):
        return await res
    return res

async def setup(bot: commands.Bot):
    await bot.add_cog(NixeBanCommands(bot))
