from __future__ import annotations
import os, re, json, logging
from typing import List, Set
import discord
from discord.ext import commands
from ..helpers.urltools import extract_urls, domain_from_url
from ..helpers.banlog import get_ban_log_channel
from .ban_embed import build_ban_embed
from ..config.self_learning_cfg import LOG_CHANNEL_ID, LINK_DB_MARKER
log = logging.getLogger(__name__)
def _load_blacklist_from_content(content: str) -> Set[str]:
    m = re.search(r"```json\s*(\{.*?\})\s*```", content or '', re.I | re.S)
    out: Set[str] = set()
    if m:
        try:
            obj = json.loads(m.group(1))
            arr = obj.get('domains') or obj.get('items') or []
            for it in arr:
                if isinstance(it, str): out.add(it.strip().lower())
        except Exception: pass
    else:
        for line in (content or '').splitlines():
            line = line.strip().lower()
            if not line or line.startswith('#'): continue
            if ' ' in line: continue
            if '.' in line: out.add(line)
    return out
async def _get_blacklist(guild: discord.Guild) -> Set[str]:
    ch = None
    if LOG_CHANNEL_ID: ch = guild.get_channel(LOG_CHANNEL_ID)
    if not isinstance(ch, discord.TextChannel):
        for c in guild.text_channels:
            if c.name.lower() in {'log-botphising','log-botphishing','log_botphising','log-phishing'}:
                ch = c; break
    if not isinstance(ch, discord.TextChannel): return set()
    async for m in ch.history(limit=100):
        if LINK_DB_MARKER in (m.content or ''):
            return _load_blacklist_from_content(m.content or '')
    return set()
class LinkPhishGuard(commands.Cog):
    def __init__(self, bot: commands.Bot): self.bot = bot
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message or message.author.bot: return
        urls = extract_urls(message.content or '')
        if not urls: return
        bl = await _get_blacklist(message.guild)
        if not bl: return
        hit = None
        for u in urls:
            d = domain_from_url(u)
            if d in bl or any(d.endswith('.'+x) for x in bl):
                hit = d; break
        if not hit: return
        logch = get_ban_log_channel(message.guild)
        if not logch: return
        moderator = message.guild.me
        e = build_ban_embed(simulate=True, actor=moderator, target=message.author, reason=f'Link blacklist: {hit}')
        await logch.send(embed=e, allowed_mentions=discord.AllowedMentions.none())
async def setup(bot: commands.Bot):
    await bot.add_cog(LinkPhishGuard(bot))
