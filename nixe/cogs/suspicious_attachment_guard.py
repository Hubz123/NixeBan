# -*- coding: utf-8 -*-
from __future__ import annotations
import logging, time
from typing import List, Tuple, Dict
from urllib.parse import urlparse
import discord
from discord.ext import commands, tasks
from nixe.helpers.env_reader import get as _cfg_get, get_int as _cfg_int, get_bool01 as _cfg_bool01
log = logging.getLogger(__name__)
_DEFAULT_HOSTS = {"cdn.discordapp.com","media.discordapp.net","images-ext-2.discordapp.net","discord.com","discordapp.com","tenor.com","i.imgur.com","imgur.com"}
_DEFAULT_EXTS = {"png","jpg","jpeg","gif","webp"}
class SuspiciousAttachmentGuard(commands.Cog):
    def __init__(self, bot):
        self.bot=bot
        self.enabled = _cfg_bool01("SUS_ATTACH_ENABLE","1")=="1"
        self.delete_threshold = max(2, _cfg_int("SUS_ATTACH_DELETE_THRESHOLD", 3))
        self.window_s = max(120, _cfg_int("SUS_ATTACH_WINDOW_S", 600))
        self.head_timeout = max(500, _cfg_int("SUS_ATTACH_HEAD_TIMEOUT_MS", 2000))/1000.0
        self.autoban = _cfg_bool01("SUS_ATTACH_AUTOBAN_ENABLE","0")=="1"
        self.autoban_score = max(4, _cfg_int("SUS_ATTACH_AUTOBAN_SCORE", 5))
        hosts = _cfg_get("SUS_ATTACH_ALLOWED_HOSTS", ",".join(sorted(_DEFAULT_HOSTS))).split(",")
        self.allowed_hosts = {h.strip().lower() for h in hosts if h.strip()}
        exts = _cfg_get("SUS_ATTACH_ALLOWED_EXTS", ",".join(sorted(_DEFAULT_EXTS))).split(",")
        self.allowed_exts = {e.strip(".").lower() for e in exts if e.strip()}
        self._score: Dict[int, List[Tuple[float,int]]] = {}
        if self.enabled: self._gc.start()
    def cog_unload(self):
        try: self._gc.cancel()
        except Exception: pass
    @tasks.loop(seconds=90)
    async def _gc(self):
        now=time.time(); cut=now-self.window_s
        for uid, arr in list(self._score.items()):
            self._score[uid]=[(t,s) for (t,s) in arr if t>=cut]
            if not self._score[uid]: self._score.pop(uid,None)
    async def _score_url(self, url: str) -> int:
        sc=0
        try:
            from aiohttp import ClientSession
            u=urlparse(url); host=(u.hostname or "").lower(); ext=(u.path.rsplit(".",1)[-1].lower() if "." in u.path else "")
            if host not in self.allowed_hosts: sc+=2
            if ext and ext not in self.allowed_exts: sc+=2
            async with ClientSession() as s:
                try:
                    async with s.head(url, timeout=self.head_timeout, allow_redirects=True) as r:
                        c = r.headers.get("Content-Type","").lower()
                        if r.status>=400: sc+=1
                        if "image/" not in c: sc+=2
                except Exception: sc+=1
        except Exception:
            sc+=1
        return sc
    async def _check(self, msg: discord.Message):
        if not self.enabled or msg.author.bot: return
        urls=[]
        urls+= [a.url for a in msg.attachments]
        for e in msg.embeds:
            if e.url: urls.append(e.url)
            if e.image and getattr(e.image, "url", None): urls.append(e.image.url)
        if not urls: return
        tot=0
        for u in urls[:4]:
            tot+= await self._score_url(u)
            if tot>=self.delete_threshold: break
        if tot>=self.delete_threshold:
            try: await msg.delete(reason=f"suspicious attachment (score={tot})")
            except discord.Forbidden: log.warning("[sus-attach] missing Manage Messages in #%s", getattr(msg.channel,'name','?'))
            except Exception as e: log.warning("[sus-attach] delete failed: %r", e)
            # score is kept in memory window
    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        try: await self._check(msg)
        except Exception as e: log.warning("[sus-attach] err: %r", e)
async def setup(bot): 
    try: await bot.add_cog(SuspiciousAttachmentGuard(bot)); log.info("[sus-attach] loaded")
    except Exception as e: log.error("[sus-attach] setup failed: %r", e)
