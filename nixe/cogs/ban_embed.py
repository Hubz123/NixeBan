# nixe/cogs/ban_embed.py
from __future__ import annotations
from typing import Optional
import discord

LEINA_COLOR_BAN = 0xD72638      # Merah BAN
LEINA_COLOR_SIM = 0xF39C12      # Oranye Simulasi/Test

def build_ban_embed(*, simulate: bool, actor: discord.abc.User, target: discord.abc.User,
                    reason: str = "-", evidence_url: Optional[str] = None,
                    phash: Optional[str] = None, source: str = "manual") -> discord.Embed:
    title = "Test Ban (Simulasi)" if simulate else "BAN"
    color = LEINA_COLOR_SIM if simulate else LEINA_COLOR_BAN
    e = discord.Embed(title=title, color=color)

    e.add_field(name="Target", value=f"{getattr(target,'mention','?')} (`{getattr(target,'id','?')}`)", inline=False)
    e.add_field(name="Reason", value=reason or "-", inline=False)
    if evidence_url:
        e.add_field(name="Evidence", value=f"[Link]({evidence_url})", inline=False)
    if phash:
        e.add_field(name="pHash", value=f"```{phash}```", inline=False)

    e.add_field(name="Actor", value=f"{getattr(actor,'mention','?')} (`{getattr(actor,'id','?')}`)", inline=True)
    e.add_field(name="Source", value=source or "-", inline=True)

    try:
        e.set_thumbnail(url=getattr(target, "display_avatar", getattr(target, "avatar", None)).url)
    except Exception:
        pass
    e.set_footer(text="Leina-style • nixe")
    return e
