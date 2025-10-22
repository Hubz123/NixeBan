
from __future__ import annotations
import logging
from typing import Optional, Union
import discord
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

def _now_wib_str() -> str:
    t = datetime.utcnow() + timedelta(hours=7)
    return t.strftime("%Y-%m-%d %H:%M:%S") + " WIB"

def _safe_name(u: Union[discord.User, discord.Member, None]) -> str:
    if not u: return "Unknown"
    name = getattr(u, "name", None) or "Unknown"
    discr = getattr(u, "discriminator", None)
    if discr and discr != "0": return f"{name}#{discr}"
    return name

def _thumb_url(u: Union[discord.User, discord.Member, None]) -> Optional[str]:
    try:
        if u and u.display_avatar:
            return str(u.display_avatar.url)
    except Exception:
        return None
    return None

def build_ban_embed(target, moderator, reason: Optional[str] = None, *, simulate: Optional[bool] = None, dry_run: Optional[bool] = None, guild: Optional[discord.Guild] = None, **kwargs) -> discord.Embed:
    is_sim = bool(simulate or dry_run)
    title = "💀 Test Ban (Simulasi)" if is_sim else "⛔ Ban"
    color = discord.Color.red()
    embed = discord.Embed(title=title, color=color)

    if target:
        mention = getattr(target, "mention", None) or f"`{_safe_name(target)}`"
        tid = getattr(target, "id", None)
        target_val = f"{mention} ({tid})" if tid else f"{mention}"
    else:
        target_val = "—"
    mod_val = getattr(moderator, "mention", None) if moderator else "—"
    embed.add_field(name="Target:", value=target_val, inline=False)
    embed.add_field(name="Moderator:", value=mod_val or "—", inline=False)
    embed.add_field(name="Reason:", value=(reason if (reason and str(reason).strip()) else "—"), inline=False)

    if is_sim:
        embed.description = "*Ini hanya simulasi. Tidak ada aksi ban yang dilakukan.*"
    turl = _thumb_url(target)
    if turl: embed.set_thumbnail(url=turl)
    embed.set_footer(text=f"SatpamBot • {_now_wib_str()}")
    return embed

from discord.ext import commands
class _BanEmbedCog(commands.Cog): ...
async def setup(bot: commands.Bot):
    await bot.add_cog(_BanEmbedCog(bot))
