from __future__ import annotations
import re, logging
import discord
from discord.ext import commands
from .ban_embed import build_ban_embed
from ..helpers.banlog import get_ban_log_channel
from ..config.self_learning_cfg import BAN_DRY_RUN, BAN_DELETE_SECONDS
log = logging.getLogger(__name__)
async def _parse_args_for_user_and_reason(ctx: commands.Context, args: str):
    user = None; reason = ''
    if not args: return None, ''
    parts = args.split()
    if not parts: return None, ''
    target_raw = parts[0]
    rest = ' '.join(parts[1:]) if len(parts) > 1 else ''
    m = re.fullmatch(r"<@!?(?P<i>\d+)>", target_raw)
    uid = int(m.group('i')) if m else (int(target_raw) if target_raw.isdigit() else None)
    if uid:
        try:
            user = ctx.guild.get_member(uid) or ctx.bot.get_user(uid) or (await ctx.bot.fetch_user(uid))
        except Exception:
            try: user = await ctx.bot.fetch_user(uid)
            except Exception: user = None
    else:
        if ctx.message.mentions:
            user = ctx.message.mentions[0]; rest = args
        else:
            user = None; rest = args
    reason = (rest or '—').strip()
    return user, reason
class NixeBanCommands(commands.Cog):
    def __init__(self, bot: commands.Bot): self.bot = bot
    def _logch(self, guild: discord.Guild):
        return get_ban_log_channel(guild)
    @commands.command(name='testban', aliases=['tb'])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def testban_cmd(self, ctx: commands.Context, *, args: str = ''):
        user, reason = await _parse_args_for_user_and_reason(ctx, args)
        if not user: return await ctx.reply('Format: `!tb @user [alasan]`', mention_author=False)
        ch = self._logch(ctx.guild)
        if not ch: return await ctx.reply('Set ENV `NIXE_BAN_LOG_CHANNEL_ID`.', mention_author=False)
        evidence_url = None
        if ctx.message.attachments:
            try: evidence_url = ctx.message.attachments[0].url
            except Exception: pass
        e = build_ban_embed(simulate=True, actor=ctx.author, target=user, reason=reason, evidence_url=evidence_url)
        await ch.send(embed=e, allowed_mentions=discord.AllowedMentions.none())
        await ctx.message.add_reaction('✅')
    @commands.command(name='ban')
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban_cmd(self, ctx: commands.Context, *, args: str = ''):
        user, reason = await _parse_args_for_user_and_reason(ctx, args)
        if not user: return await ctx.reply('Format: `!ban @user [alasan]`', mention_author=False)
        ch = self._logch(ctx.guild)
        if not ch: return await ctx.reply('Set ENV `NIXE_BAN_LOG_CHANNEL_ID`.', mention_author=False)
        dry = BAN_DRY_RUN or bool(re.search(r"\b--dry\b", reason))
        if dry: reason = re.sub(r"\s*--dry\b", '', reason).strip() or '—'
        evidence_url = None
        if ctx.message.attachments:
            try: evidence_url = ctx.message.attachments[0].url
            except Exception: pass
        e = build_ban_embed(simulate=dry, actor=ctx.author, target=user, reason=reason, evidence_url=evidence_url)
        banned_ok = False
        if not dry:
            try:
                member = ctx.guild.get_member(user.id)
                await ctx.guild.ban(member or user, reason=reason, delete_message_seconds=BAN_DELETE_SECONDS)
                banned_ok = True
            except discord.Forbidden:
                await ctx.reply('Izin ban tidak mencukupi.', mention_author=False)
            except Exception as exc:
                log.warning('Ban failed: %s', exc)
                await ctx.reply(f'Gagal ban: {exc}', mention_author=False)
        await ch.send(embed=e, allowed_mentions=discord.AllowedMentions.none())
        await ctx.message.add_reaction('✅' if (dry or banned_ok) else '⚠️')
async def setup(bot: commands.Bot):
    await bot.add_cog(NixeBanCommands(bot))
