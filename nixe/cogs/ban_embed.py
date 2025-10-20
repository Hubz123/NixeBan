from __future__ import annotations
from typing import Optional
import datetime as _dt
try:
    from zoneinfo import ZoneInfo as _ZoneInfo
except Exception:
    _ZoneInfo = None
import discord
from ..config.self_learning_cfg import BAN_BRAND_NAME
LEINA_COLOR_BAN = 0xD72638
LEINA_COLOR_SIM = 0xF39C12
def _wib_now_str():
    tz = None
    if _ZoneInfo is not None:
        try: tz = _ZoneInfo('Asia/Jakarta')
        except Exception: tz = None
    now = _dt.datetime.now(tz) if tz else _dt.datetime.now()
    return now.strftime('%Y-%m-%d %H:%M:%S') + ' WIB'
def build_ban_embed(*, simulate: bool, actor: discord.abc.User, target: discord.abc.User,
                    reason: str = '—', evidence_url: Optional[str] = None,
                    phash: Optional[str] = None) -> discord.Embed:
    title = ('💀 Test Ban (Simulasi)' if simulate else '⛔ BAN')
    color = (LEINA_COLOR_SIM if simulate else LEINA_COLOR_BAN)
    e = discord.Embed(title=title, color=color)
    e.add_field(name='Target', value=f"{getattr(target,'mention','?')} ({getattr(target,'id','?')})", inline=False)
    e.add_field(name='Moderator', value=f"{getattr(actor,'mention','?')}", inline=False)
    e.add_field(name='Reason', value=(reason or '—'), inline=False)
    if evidence_url:
        e.add_field(name='Evidence', value=f"[Link]({evidence_url})", inline=False)
    if phash:
        e.add_field(name='pHash', value=f"```{phash}```", inline=False)
    try:
        avatar = getattr(target, 'display_avatar', getattr(target, 'avatar', None))
        if avatar and hasattr(avatar, 'url'):
            e.set_thumbnail(url=avatar.url)
    except Exception:
        pass
    if simulate:
        e.description = '_Ini hanya simulasi. Tidak ada aksi ban yang dilakukan._'
    e.set_footer(text=f"{BAN_BRAND_NAME} • {_wib_now_str()}")
    return e
