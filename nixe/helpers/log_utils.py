from __future__ import annotations
import discord, time

async def upsert_status_embed_in_channel(bot, ch: discord.TextChannel):
    title = "NIXE Status"
    desc = f"✅ Online\n⏱️ Uptime: ~{int(time.time() - getattr(bot,'start_time', time.time()))}s"
    try:
        embed = discord.Embed(title=title, description=desc)
        await ch.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
    except Exception:
        pass
