
# -*- coding: utf-8 -*-
import os, io, asyncio, logging
from typing import Optional
import discord
from discord.ext import commands

# Persona helper
try:
    from nixe.helpers.persona_loader import load_persona, pick_line
except Exception:
    load_persona = None
    pick_line = None

# Image classifier bridge (respects env like LPG_PROVIDER_ORDER, models, etc)
try:
    from nixe.helpers.gemini_bridge import classify_lucky_pull_bytes as classify_bytes
except Exception:
    classify_bytes = None

log = logging.getLogger(__name__)

def _env_bool_any(*pairs, default=False):
    for k, d in pairs:
        v = os.getenv(k, d)
        if v is None: 
            continue
        if str(v).strip().lower() in ("1","true","yes","on"): 
            return True
        if str(v).strip().lower() in ("0","false","no","off"):
            return False
    return default

def _env_str_any(*keys, default=""):
    for k in keys:
        v = os.getenv(k, None)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return default

def _env_int_any(*keys, default=0):
    for k in keys:
        v = os.getenv(k, None)
        if v is None: 
            continue
        try:
            return int(str(v).strip())
        except Exception:
            continue
    return default

def _env_float_any(*keys, default=0.0):
    for k in keys:
        v = os.getenv(k, None)
        if v is None: 
            continue
        try:
            return float(str(v).strip())
        except Exception:
            continue
    return default

def _parse_id_list(value: str):
    out = set()
    for tok in (value or "").replace(" ", "").split(","):
        if tok.isdigit(): 
            out.add(int(tok))
    return out

def _provider_threshold(provider: str):
    eps = _env_float_any("LPG_CONF_EPSILON", default=0.0)
    if provider and provider.lower().startswith("gemini"):
        thr = _env_float_any("GEMINI_LUCKY_THRESHOLD", "LPG_GEMINI_THRESHOLD", default=0.80)
        return max(0.0, min(1.0, thr - eps))
    # default groq threshold
    thr = _env_float_any("LPG_GROQ_THRESHOLD", default=0.50)
    return max(0.0, min(1.0, thr - eps))

def _mention_enabled():
    return _env_bool_any(("LPG_MENTION","1"), ("LUCKYPULL_MENTION_USER","1"), default=True)

def _provider_order():
    order = _env_str_any("LPG_PROVIDER_ORDER", "LPG_IMAGE_PROVIDER_ORDER", "LPA_PROVIDER_ORDER", default="gemini,groq")
    return [p.strip().lower() for p in order.split(",") if p.strip()]

class LuckyPullGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enable = _env_bool_any(("LPG_ENABLE","1"), default=True)

        guards = _env_str_any("LPG_GUARD_CHANNELS", "LUCKYPULL_GUARD_CHANNELS", default="")
        self.guard_channels = _parse_id_list(guards)

        # Redirect channel: prefer LPG_, fallback LUCKYPULL_ then LPA_
        self.redirect_channel_id = _env_int_any("LPG_REDIRECT_CHANNEL_ID", "LUCKYPULL_REDIRECT_CHANNEL_ID", "LPA_REDIRECT_CHANNEL_ID", default=0)

        self.mention = _mention_enabled()
        self.delete_on_guard = _env_bool_any(("LUCKYPULL_DELETE_ON_GUARD","1"), default=True)

        # Provider execution order and timeout (ms)
        self.provider_order = _provider_order()
        self.timeout_ms = _env_int_any("LUCKYPULL_GEM_TIMEOUT_MS", "LPA_PROVIDER_TIMEOUT_MS", default=20000)

        # Persona mode/tone
        self.persona_mode  = os.getenv("LPG_PERSONA_MODE", "yandere")
        self.persona_tone  = os.getenv("LPG_PERSONA_TONE", "auto")

        # Load persona
        self._persona_mode, self._persona_data, self._persona_path = None, {}, None
        try:
            if load_persona:
                m, d, p = load_persona()
                if m and d:
                    self._persona_mode, self._persona_data, self._persona_path = m, d, p
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.enable:
            log.warning("[lpg] disabled via LPG_ENABLE=0"); return
        log.warning("[lpg] ready | guards=%s redirect=%s providers=%s timeout=%dms",
                    list(self.guard_channels), self.redirect_channel_id, self.provider_order, self.timeout_ms)
        if self._persona_path:
            log.warning("[lpg] persona file: %s", self._persona_path.replace("\", "/"))
        if classify_bytes is None:
            log.error("[lpg] gemini_bridge missing; classification disabled")

    def _is_guard_channel(self, channel: discord.abc.GuildChannel) -> bool:
        try: return channel and int(channel.id) in self.guard_channels
        except Exception: return False

    def _pick_tone(self, score: float) -> str:
        t = (self.persona_tone or "auto").lower()
        if t in ("soft","agro","sharp"): return t
        if score >= 0.95: return "sharp"
        if score >= 0.85: return "agro"
        return "soft"

    async def _persona_notify(self, message: discord.Message, score: float):
        tone = self._pick_tone(score)
        if pick_line and self._persona_data:
            line = pick_line(self._persona_data, self._persona_mode or self.persona_mode, tone)
        else:
            line = "Konten dipindahkan ke channel yang benar."

        channel_mention = f"<#{self.redirect_channel_id}>" if self.redirect_channel_id else f"#{message.channel.name}"
        user_mention = message.author.mention if self.mention else str(message.author)
        line = (line.replace("{user}", user_mention)
                    .replace("{user_name}", str(message.author))
                    .replace("{channel}", channel_mention)
                    .replace("{channel_name}", f"#{message.channel.name}"))

        try:
            await message.channel.send(line, reference=message, mention_author=self.mention)
        except Exception:
            await message.channel.send(line)

    async def _handle_redirect(self, message: discord.Message, score: float, provider: str, reason: str, attachments):
        if not self.redirect_channel_id: return
        chan = message.guild.get_channel(self.redirect_channel_id) if message.guild else None
        if not chan:
            try: chan = await self.bot.fetch_channel(self.redirect_channel_id)
            except Exception: chan = None
        if not chan:
            log.error("[lpg] redirect channel not found: %s", self.redirect_channel_id); return

        files = []
        for a in attachments:
            try:
                if a.size and a.size > 0:
                    b = await a.read()
                    files.append(discord.File(io.BytesIO(b), filename=a.filename))
            except Exception as e:
                log.warning("[lpg] attach read fail: %s", e)

        desc = "Score **{:.3f}** via `{}`\nReason: {}".format(score, provider, reason)
        content = (message.author.mention if self.mention else None)
        embed = discord.Embed(title="Lucky Pull terdeteksi", description=desc, color=0xFF66AA)
        embed.add_field(name="Pengirim", value="{} ({})".format(message.author.mention if self.mention else "", message.author), inline=False)
        embed.add_field(name="Sumber", value="#{}".format(message.channel.name), inline=True)
        embed.set_footer(text="msg_id={}".format(message.id))
        try:
            await chan.send(content=content, embed=embed, files=files or None)
        except Exception as e:
            log.error("[lpg] redirect send failed: %s", e)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.enable or message.author.bot: return
        if not self._is_guard_channel(getattr(message, "channel", None)): return
        if not message.attachments: return

        img_attachments = [a for a in message.attachments if (a.content_type or "").startswith("image/")]
        if not img_attachments: return
        first = img_attachments[0]
        try: img_bytes = await first.read()
        except Exception: return

        ok, score, provider, reason = (False, 0.0, "none", "bridge_unavailable")
        if classify_bytes is not None:
            try:
                ok, score, provider, reason = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: classify_bytes(img_bytes, timeout_ms=self.timeout_ms, providers=self.provider_order)
                )
            except Exception as e:
                log.error("[lpg] classify error: %s", e)

        # Check threshold per provider
        passed = False
        if ok:
            thr = _provider_threshold(provider)
            passed = (score >= thr)
        log.warning("[lpg] chan=%s user=%s score=%.3f thr=%.3f provider=%s pass=%s reason=%s",
                    message.channel.id, message.author, score, _provider_threshold(provider), provider, passed, reason)

        if not passed:
            return

        # Action: always redirect, optionally delete original (per env)
        await self._persona_notify(message, score)
        await self._handle_redirect(message, score, provider, reason, img_attachments)

        if self.delete_on_guard:
            try: await message.delete(delay=0)
            except Exception as e: log.error("[lpg] delete failed: %s", e)

    @commands.group(name="lpg", invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def lpg(self, ctx: commands.Context):
        await ctx.send("Subcommands: `!lpg config`, `!lpg test-persona [soft|agro|sharp]`, `!lpg test-redirect [#chan|id]`")

    @lpg.command(name="config")
    @commands.has_permissions(manage_messages=True)
    async def lpg_config(self, ctx: commands.Context):
        e = discord.Embed(title="LPG Config", color=0x99CCFF)
        e.add_field(name="Enabled", value=str(self.enable))
        e.add_field(name="Guard Channels", value=", ".join(map(str, self.guard_channels)) or "-", inline=False)
        e.add_field(name="Redirect", value=str(self.redirect_channel_id))
        e.add_field(name="Mention", value=str(self.mention))
        e.add_field(name="DeleteOnGuard", value=str(self.delete_on_guard))
        e.add_field(name="Providers", value=", ".join(self.provider_order))
        e.add_field(name="Timeout(ms)", value=str(self.timeout_ms))
        e.add_field(name="Persona", value="{}/{} @ {}".format(self._persona_mode or self.persona_mode, self.persona_tone, (self._persona_path or "-").replace("\","/")))
        await ctx.send(embed=e)

    @lpg.command(name="test-persona")
    @commands.has_permissions(manage_messages=True)
    async def lpg_test_persona(self, ctx: commands.Context, tone: Optional[str] = None):
        t = (tone or self.persona_tone or "soft")
        fake_score = 0.96 if t=="sharp" else (0.90 if t=="agro" else 0.78)
        if pick_line and self._persona_data:
            line = pick_line(self._persona_data, self._persona_mode or self.persona_mode, self._pick_tone(fake_score))
        else:
            line = "Persona default."
        channel_mention = f"<#{self.redirect_channel_id}>" if self.redirect_channel_id else f"#{ctx.channel.name}"
        user_mention = ctx.author.mention if self.mention else str(ctx.author)
        line = (line.replace("{user}", user_mention)
                    .replace("{user_name}", str(ctx.author))
                    .replace("{channel}", channel_mention)
                    .replace("{channel_name}", f"#{ctx.channel.name}"))
        await ctx.send(line)

    @lpg.command(name="test-redirect")
    @commands.has_permissions(manage_messages=True)
    async def lpg_test_redirect(self, ctx: commands.Context, target: Optional[str] = None):
        chan_id = self.redirect_channel_id
        if target:
            if target.isdigit():
                chan_id = int(target)
            elif ctx.message.channel_mentions:
                chan_id = ctx.message.channel_mentions[0].id
        ch = ctx.guild.get_channel(chan_id) if ctx.guild else None
        if not ch:
            try: ch = await self.bot.fetch_channel(chan_id)
            except Exception: ch = None
        if not ch:
            await ctx.send("Gagal: channel {} tidak ditemukan.".format(chan_id)); return
        embed = discord.Embed(title="Test Redirect OK", description="Tes dari !lpg test-redirect", color=0x66FFCC)
        await ch.send(embed=embed, content=(ctx.author.mention if self.mention else None))
        await ctx.send("Sent to <#{}>".format(chan_id))

def setup(bot: commands.Bot):
    if _env_str_any("LPG_COG_ENABLE", default="1") in ("0","false","no"):
        return
    bot.add_cog(LuckyPullGuard(bot))
