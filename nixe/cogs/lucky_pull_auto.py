
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, re, logging, asyncio, random
from typing import Iterable, Tuple, List, Optional, Any
import discord
from discord.ext import commands

log = logging.getLogger("nixe.cogs.lucky_pull_auto")

# ---- Optional bus (for cross-cog cancellation) ----
try:
    from nixe.shared import bus  # must provide mark_deleted(id) & is_deleted(id)
except Exception:
    class _BusStub:
        @staticmethod
        def mark_deleted(msg_id: int, ttl: int = 15) -> None:
            pass
        @staticmethod
        def is_deleted(msg_id: int) -> bool:
            return False
    bus = _BusStub()

# ---- Optional Gemini bridge ----
try:
    from nixe.helpers.gemini_bridge import classify_lucky_pull  # async -> (label, conf)
except Exception as e:
    log.debug("[lpa] gemini helper not available: %r", e)
    async def classify_lucky_pull(images: Iterable[bytes], hints: str = "", timeout_ms: int = 10000) -> Tuple[str, float]:
        # Safe fallback: never claims "lucky"
        return "other", 0.0

# ---- Helpers ----
def _env_get(*names: str, default: str | None = None) -> str | None:
    for n in names:
        v = os.getenv(n)
        if v is not None:
            return v
    return default

def _float_env(*names: str, default: float = 0.0) -> float:
    v = _env_get(*names)
    try:
        return float(v) if v is not None else float(default)
    except Exception:
        return float(default)

def _parse_id_list(s: str | None) -> List[str]:
    s = (s or "").replace(";", ",")
    return [x.strip() for x in s.split(",") if x.strip()]

def _pick_tone() -> str:
    mode = _env_get("YANDERE_TONE_MODE") or "random"
    if mode != "random":
        return _env_get("YANDERE_TONE_FIXED") or "soft"
    weights = {"soft": 0.3, "agro": 0.5, "sharp": 0.3}
    try:
        for k in list(weights):
            ev = _env_get(f"YANDERE_WEIGHT_{k.upper()}")
            if ev is not None:
                weights[k] = float(ev)
    except Exception:
        pass
    g = random.random() * sum(weights.values())
    c = 0.0
    for k, w in weights.items():
        c += w
        if g <= c:
            return k
    return "soft"

def _format_notice(tone: str, author: discord.abc.User, redirect_id: str | None) -> str:
    tag = author.mention if getattr(author, "mention", None) else f"<@{getattr(author, 'id', 'user')}>"
    dest = f"<#{redirect_id}>" if redirect_id else "channel yang benar"
    if tone == "agro":
        return f"{tag} lucky pull di sini dilarang. Pindahkan ke {dest} ya."
    if tone == "sharp":
        return f"{tag} ini bukan tempat lucky pull. Silakan pindah ke {dest}."
    return f"{tag} jangan post lucky pull di sini. Mohon pindah ke {dest} ya."

async def _send_notice(ch: discord.abc.Messageable, content: str, ttl: int = 20):
    try:
        msg = await ch.send(content)
        await asyncio.sleep(max(1, int(ttl)))
        await msg.delete()
    except Exception:
        pass

def _is_image_name(name: str) -> bool:
    n = (name or "").lower()
    return bool(re.search(r"\.(png|jpe?g|gif|bmp|webp)$", n))

def _sniff(buf: bytes) -> str:
    b = buf or b""
    if len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP": return "image/webp"
    if b.startswith(b"\x89PNG\r\n\x1a\n"): return "image/png"
    if b[:2] == b"\xff\xd8": return "image/jpeg"
    if b[:6] in (b"GIF87a", b"GIF89a"): return "image/gif"
    if b[:2] == b"BM": return "image/bmp"
    return "application/octet-stream"

class LuckyPullAuto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Channels & policy
        chs = _env_get("LPA_GUARD_CHANNELS","LPG_GUARD_CHANNELS","LUCKYPULL_GUARD_CHANNELS","GUARD_CHANNELS","LUCKYPULL_CHANNELS","")
        self.guard_channels: List[str] = _parse_id_list(chs)
        self.redirect_id: str = _env_get("LPA_REDIRECT_CHANNEL_ID","LPG_REDIRECT_CHANNEL_ID","LUCKYPULL_REDIRECT_CHANNEL_ID","LUCKYPULL_REDIRECT","REDIRECT_CHANNEL_ID","") or ""

        self.delete_on_guard: bool = bool(int(_env_get("LPA_DELETE_ON_GUARD","LUCKYPULL_DELETE_ON_GUARD","LPG_DELETE_ON_GUARD","1") or "1"))
        self.mention_user: bool = bool(int(_env_get("LPA_MENTION_USER","LUCKYPULL_MENTION_USER","LPG_MENTION_USER","1") or "1"))
        self.strict_on_guard: bool = bool(int(_env_get("LPA_STRICT_ON_GUARD","LUCKYPULL_STRICT_ON_GUARD","LPG_STRICT_ON_GUARD","0") or "0"))
        self.force_delete_test: bool = bool(int(_env_get("LPA_FORCE_DELETE_TEST","LPG_FORCE_DELETE_TEST","0") or "0"))

        # Thresholds
        self.threshold = _float_env("GEMINI_LUCKY_THRESHOLD","LUCKYPULL_GEMINI_THRESHOLD", default=0.80)
        self.fast_enable = bool(int(_env_get("LPG_FAST_PATH_ENABLE","LPA_FAST_PATH_ENABLE","1") or "1"))
        self.fast_delete_thr = _float_env("LPG_FAST_DELETE_THRESHOLD","LPA_FAST_DELETE_THRESHOLD", default=max(self.threshold, 0.90))

        # Gemini classify params
        self.timeout_ms = int(float(_env_get("LUCKYPULL_GEM_TIMEOUT_MS","LPG_GEM_TIMEOUT_MS","GEMINI_TIMEOUT_MS","10000") or "10000"))
        self.hints = _env_get("GEMINI_LUCKY_HINTS","LUCKYPULL_HINTS","") or "gacha pull results grid star icons rainbow/gold beam"

        # Notice
        self.notice_enable: bool = bool(int(_env_get("LPA_NOTICE_ENABLE","LUCKYPULL_NOTICE_ENABLE","1") or "1"))
        self.notice_ttl: int = int(float(_env_get("LPA_NOTICE_TTL","LUCKYPULL_NOTICE_TTL","20") or "20"))
        # NEW: notice on fast path toggle (default ON)
        self.notice_on_fast: bool = bool(int(_env_get("LPA_NOTICE_ON_FAST","1") or "1"))

        log.info("[lpa] guard_channels=%s redirect=%s del=%s mention=%s thr=%.2f fast(%s,%.2f)",
                 self.guard_channels, self.redirect_id, self.delete_on_guard, self.mention_user,
                 self.threshold, self.fast_enable, self.fast_delete_thr)

    async def _collect_images(self, message: discord.Message) -> List[bytes]:
        blobs: List[bytes] = []
        try:
            for att in getattr(message, "attachments", []) or []:
                if getattr(att, "size", 0) <= 0:
                    continue
                try:
                    data = await att.read(use_cached=True)
                    if _sniff(data).startswith("image/"):
                        blobs.append(data)
                except Exception:
                    pass
                if len(blobs) >= 2:
                    break
        except Exception:
            pass
        return blobs

    async def _classify(self, blobs: List[bytes]) -> Tuple[str, float]:
        try:
            return await classify_lucky_pull(blobs, hints=self.hints, timeout_ms=self.timeout_ms)
        except Exception as e:
            log.warning("[lpa] classify error: %r", e)
            return "other", 0.0

    async def _maybe_notice(self, message: discord.Message):
        if not self.notice_enable:
            return
        try:
            tone = _pick_tone()
            content = _format_notice(tone, message.author, self.redirect_id)
            await _send_notice(message.channel, content, self.notice_ttl)
        except Exception as e:
            log.debug("[lpa] notice failed: %r", e)

    @commands.Cog.listener("on_message")
    async def _on_message(self, message: discord.Message):
        try:
            if message.author.bot:
                return
            in_guard = str(message.channel.id) in self.guard_channels if self.guard_channels else False
            if not in_guard:
                return
        except Exception:
            return

        imgs = await self._collect_images(message)
        if not imgs:
            return

        if self.force_delete_test or self.strict_on_guard:
            label, conf = "lucky", 1.0
            log.warning("[lpa] TEST/STRICT fallback => lucky=1.0")
        else:
            label, conf = await self._classify(imgs)

        log.info("[lpa] classify: result=(%s, %.3f) thr=%.2f", label, conf, self.threshold)

        # FAST PATH
        if self.fast_enable and label == "lucky" and conf >= self.fast_delete_thr and self.delete_on_guard:
            try:
                await message.delete()
                bus.mark_deleted(message.id)
                log.info("[lpa] fast-deleted a message in %s (reason=lucky pull)", message.channel.id)
            except Exception as e:
                log.warning("[lpa] fast-delete failed: %r", e)
            # NEW: notice even on fast path (if enabled)
            if self.notice_on_fast:
                await self._maybe_notice(message)
            return

        # NORMAL PATH
        if label == "lucky" and conf >= self.threshold and self.delete_on_guard:
            try:
                await message.delete()
                bus.mark_deleted(message.id)
                log.info("[lpa] deleted a message in %s (reason=lucky pull)", message.channel.id)
            except Exception as e:
                log.warning("[lpa] delete failed: %r", e)

            await self._maybe_notice(message)

async def setup(bot: commands.Bot):
    await bot.add_cog(LuckyPullAuto(bot))
