\
import logging, re
from typing import List
from discord.ext import commands, tasks
import discord

from nixe.config import load
from nixe.helpers.urltools import extract_domains, normalize_domain
import os
LINK_DB_CHANNEL_NAME = os.getenv('LINK_DB_CHANNEL_NAME','log-botphising')

log = logging.getLogger("nixe.link_phish_guard")
cfg = load().link

def _compile_regexes(pats: List[str]) -> List[re.Pattern]:
    out = []
    for p in pats:
        try: out.append(re.compile(p, re.I))
        except re.error: log.warning("Invalid regex ignored: %s", p)
    return out

class LinkPhishGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._compiled = _compile_regexes(cfg.regexes)
        self.blacklist = set(normalize_domain(d) for d in cfg.blacklist_domains)
        self.refresh_task.start()

    def cog_unload(self): self.refresh_task.cancel()

    @tasks.loop(minutes=15.0)
    async def refresh_task(self):
        await self._refresh_from_channel()

    @refresh_task.before_loop
    async def _before(self): await self.bot.wait_until_ready()

    async def _refresh_from_channel(self):
        if not cfg.db_channel_id: return
        ch = self.bot.get_channel(cfg.db_channel_id)
        if not ch and LINK_DB_CHANNEL_NAME:
            # try find by name in any guild
            for g in self.bot.guilds:
                for c in g.text_channels:
                    if c.name.lower() == LINK_DB_CHANNEL_NAME.lower():
                        ch = c; break
                if ch: break
        if not ch: return
        try:
            pins = []
            try: pins = await ch.pins()
            except Exception: pass
            texts = [m.content or "" for m in pins] if pins else []
            if not texts:
                async for m in ch.history(limit=200):
                    texts.append(m.content or "")
            new_domains = set()
            new_regexes = []
            for t in texts:
                for dom in extract_domains(t): new_domains.add(dom)
                for m in re.findall(r"regex:\\s*(.+)", t, re.I): new_regexes.append(m.strip())
            if new_domains: self.blacklist |= new_domains
            if new_regexes: self._compiled.extend(_compile_regexes(new_regexes))
            log.info("[link-db] domains=%d regexes=%d", len(self.blacklist), len(self._compiled))
        except Exception as e:
            log.exception("link-db refresh error: %s", e)

    def _match(self, text: str) -> bool:
        t = text or ""
        for d in self.blacklist:
            if d and d in t.lower(): return True
        for r in self._compiled:
            if r.search(t): return True
        return False

    async def _act(self, message: discord.Message, reason: str):
        if not cfg.enable_automod:
            log.info("[link-dryrun] would act on %s: %s", message.id, reason); return
        try:
            if cfg.autoban_on_match and message.guild.me.guild_permissions.ban_members:
                await message.author.ban(reason=reason, delete_message_days=cfg.delete_message_days)
                log.info("[link-ban] %s (%s) %s", message.author, message.author.id, reason); return
            await message.delete()
            await message.channel.send(f"⚠️ Link terindikasi phish dari {message.author.mention} dihapus.", delete_after=6)
            log.info("[link-del] %s: %s", message.id, reason)
        except Exception as e:
            log.exception("link action failed: %s", e)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if message.author.bot or message.guild is None: return
            content = " ".join([message.content or ""] + [e.url for e in message.embeds if hasattr(e, "url") and e.url])
            domains = extract_domains(content)
            if (domains and any((d in self.blacklist) for d in domains)) or self._match(content):
                await self._act(message, "link blacklisted/regex match")
        except Exception as e:
            log.exception("[link-guard] on_message error: %s", e)

    @commands.command(name="linkguard")
    @commands.has_permissions(manage_guild=True)
    async def linkguard_cmd(self, ctx: commands.Context, sub: str = "status"):
        if sub == "reload":
            await self._refresh_from_channel()
            await ctx.reply(f"Reloaded. domains={len(self.blacklist)} regexes={len(self._compiled)}")
            return
        await ctx.reply(f"status: automod={'ON' if cfg.enable_automod else 'OFF'} "
                        f"autoban={'ON' if cfg.autoban_on_match else 'OFF'} "
                        f"domains={len(self.blacklist)} regexes={len(self._compiled)}")
    
async def setup(bot: commands.Bot):
    await bot.add_cog(LinkPhishGuard(bot))
