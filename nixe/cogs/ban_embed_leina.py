from __future__ import annotations
from typing import Optional, Union
from datetime import datetime, timedelta
import discord
from ..config_ids import BAN_BRAND_NAME
DANGER_RED = discord.Color(0xED4245)
def _wib_now_str() -> str:
    t = datetime.utcnow() + timedelta(hours=7)
    return t.strftime("%Y-%m-%d %H:%M:%S") + " WIB"
def _safe_name(u: Union[discord.Member, discord.User, None]) -> str:
    if not u: return "-"
    try: return f"{u.mention} ({u.id})"
    except Exception: return f"{getattr(u,'name','?')} ({getattr(u,'id','?')})"
def build_testban_embed(*, target: Union[discord.Member, discord.User, None], moderator: Union[discord.Member, discord.User, None], reason: Optional[str]=None, evidence_url: Optional[str]=None) -> discord.Embed:
    title = "💀 Test Ban (Simulasi)"
    desc = "\n".join([f"**Target:** {_safe_name(target)}", f"**Moderator:** {_safe_name(moderator)}", f"**Reason:** {reason or '—'}", "", "*Ini hanya simulasi. Tidak ada aksi ban yang dilakukan.*"])
    emb = discord.Embed(title=title, description=desc, colour=DANGER_RED)
    try:
        if target and target.display_avatar: emb.set_thumbnail(url=str(target.display_avatar.url))
    except Exception: pass
    if evidence_url: emb.set_image(url=evidence_url)
    emb.set_footer(text=f"{BAN_BRAND_NAME} • {_wib_now_str()}"); return emb
def build_banned_embed(*, target: Union[discord.Member, discord.User, None], moderator: Union[discord.Member, discord.User, None], reason: Optional[str]=None, evidence_url: Optional[str]=None) -> discord.Embed:
    title = "💀 BANNED"
    desc = "\n".join([f"**Target:** {_safe_name(target)}", f"**Moderator:** {_safe_name(moderator)}", f"**Reason:** {reason or '—'}"])
    emb = discord.Embed(title=title, description=desc, colour=DANGER_RED)
    try:
        if target and target.display_avatar: emb.set_thumbnail(url=str(target.display_avatar.url))
    except Exception: pass
    if evidence_url: emb.set_image(url=evidence_url)
    emb.set_footer(text=f"{BAN_BRAND_NAME} • {_wib_now_str()}"); return emb
from discord.ext import commands
class _EmbedShim(commands.Cog): pass
async def setup(bot: commands.Bot): await bot.add_cog(_EmbedShim(bot))
def setup_legacy(bot: commands.Bot): bot.add_cog(_EmbedShim(bot))
