
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, re, logging, asyncio, random, json, pathlib
from typing import Iterable, Tuple, List, Optional, Any, Dict
import discord
from discord.ext import commands

log = logging.getLogger("nixe.cogs.lucky_pull_auto")

try:
    from nixe.shared import bus
except Exception:
    class _BusStub:
        @staticmethod
        def mark_deleted(msg_id: int, ttl: int = 15) -> None: pass
        @staticmethod
        def is_deleted(msg_id: int) -> bool: return False
    bus = _BusStub()

try:
    from nixe.helpers.gemini_bridge import classify_lucky_pull
except Exception as e:
    log.debug("[lpa] gemini helper not available: %r", e)
    async def classify_lucky_pull(images, hints: str = "", timeout_ms: int = 10000):
        return "other", 0.0

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

def _safe_mention(user) -> str:
    return getattr(user, "mention", None) or f"<@{getattr(user, 'id', 'user')}>"

def _chan_mention(cid: str | None) -> str:
    return f"<#{cid}>" if cid else "channel yang benar"

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

def _load_persona_templates() -> Dict[str, Any]:
    p = _env_get("PERSONA_PROFILE_PATH", "YANDERE_TEMPLATES_PATH", default="nixe/config/personas/yandere.json")
    try:
        from pathlib import Path
        path = Path(p)
        if not path.exists():
            path = Path.cwd() / p
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        log.debug("[lpa] persona templates failed to load from %r: %r", p, e)
        return {}

def _pick_template(tpl: Dict[str, Any], tone: str) -> Optional[str]:
    candidates = []
    for key in ("lpg_notice", "lucky_pull_notice", "notice"):
        s = tpl.get(key) if isinstance(tpl, dict) else None
        if isinstance(s, dict):
            arr = s.get(tone) or s.get("generic")
            if isinstance(arr, list) and arr:
                candidates.extend(arr)
    if not candidates and tone in tpl and isinstance(tpl[tone], list):
        candidates.extend(tpl[tone])
    if not candidates and isinstance(tpl.get("generic"), list):
        candidates.extend(tpl["generic"])
    if not candidates:
        return None
    import random as _r
    return _r.choice(candidates)

def _render_notice(raw: str, author, redirect_id: str | None, mention_user: bool) -> str:
    tag = _safe_mention(author) if mention_user else (getattr(author, "display_name", None) or getattr(author, "name", "user"))
    dest = _chan_mention(redirect_id)
    rep = {
        "{user}": tag,
        "{username}": getattr(author, "name", "user"),
        "{display}": getattr(author, "display_name", getattr(author, "name", "user")),
        "{channel}": dest,
        "{redirect}": dest,
    }
    out = raw
    for k, v in rep.items():
        out = out.replace(k, v)
    return out

class LuckyPullAuto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        chs = _env_get("LPA_GUARD_CHANNELS","LPG_GUARD_CHANNELS","LUCKYPULL_GUARD_CHANNELS","GUARD_CHANNELS","LUCKYPULL_CHANNELS","")
        self.guard_channels: List[str] = _parse_id_list(chs)
        self.redirect_id: str = _env_get("LPA_REDIRECT_CHANNEL_ID","LPG_REDIRECT_CHANNEL_ID","LUCKYPULL_REDIRECT_CHANNEL_ID","LUCKYPULL_REDIRECT","REDIRECT_CHANNEL_ID","") or ""
        self.delete_on_guard: bool = bool(int(_env_get("LPA_DELETE_ON_GUARD","LUCKYPULL_DELETE_ON_GUARD","LPG_DELETE_ON_GUARD","1") or "1"))
        self.mention_user: bool = bool(int(_env_get("LPA_MENTION_USER","LUCKYPULL_MENTION_USER","LPG_MENTION_USER","1") or "1"))
        self.strict_on_guard: bool = bool(int(_env_get("LPA_STRICT_ON_GUARD","LUCKYPULL_STRICT_ON_GUARD","LPG_STRICT_ON_GUARD","0") or "0"))
        self.force_delete_test: bool = bool(int(_env_get("LPA_FORCE_DELETE_TEST","LPG_FORCE_DELETE_TEST","0") or "0"))
        self.threshold = _float_env("GEMINI_LUCKY_THRESHOLD","LUCKYPULL_GEMINI_THRESHOLD", default=0.80)
        self.fast_enable = bool(int(_env_get("LPG_FAST_PATH_ENABLE","LPA_FAST_PATH_ENABLE","1") or "1"))
        self.fast_delete_thr = _float_env("LPG_FAST_DELETE_THRESHOLD","LPA_FAST_DELETE_THRESHOLD", default=max(self.threshold, 0.90))
        self.timeout_ms = int(float(_env_get("LUCKYPULL_GEM_TIMEOUT_MS","LPG_GEM_TIMEOUT_MS","GEMINI_TIMEOUT_MS","10000") or "10000"))
        self.hints = _env_get("GEMINI_LUCKY_HINTS","LUCKYPULL_HINTS","") or "gacha pull results grid star icons rainbow/gold beam"
        self.notice_enable: bool = bool(int(_env_get("LPA_NOTICE_ENABLE","LUCKYPULL_NOTICE_ENABLE","1") or "1"))
        self.notice_ttl: int = int(float(_env_get("LPA_NOTICE_TTL","LUCKYPULL_NOTICE_TTL","20") or "20"))
        self.notice_on_fast: bool = bool(int(_env_get("LPA_NOTICE_ON_FAST","1") or "1"))
        self._persona_tpl = _load_persona_templates()
        log.info("[lpa] persona templates: %s", "loaded" if self._persona_tpl else "none")
        log.info("[lpa] guard_channels=%s redirect=%s del=%s mention=%s thr=%.2f fast(%s,%.2f)",
                 self.guard_channels, self.redirect_id, self.delete_on_guard, self.mention_user,
                 self.threshold, self.fast_enable, self.fast_delete_thr)

    async def _collect_images(self, message: discord.Message) -> List[bytes]:
        blobs: List[bytes] = []
        try:
            for att in getattr(message, "attachments", []) or []:
                if getattr(att, "size", 0) <= 0: continue
                try:
                    data = await att.read(use_cached=True)
                    if _sniff(data).startswith("image/"):
                        blobs.append(data)
                except Exception: pass
                if len(blobs) >= 2: break
        except Exception: pass
        return blobs

    async def _classify(self, blobs: List[bytes]) -> Tuple[str, float]:
        try:
            return await classify_lucky_pull(blobs, hints=self.hints, timeout_ms=self.timeout_ms)
        except Exception as e:
            log.warning("[lpa] classify error: %r", e)
            return "other", 0.0

    async def _send_notice(self, message: discord.Message):
        if not self.notice_enable:
            return
        try:
            tone = _pick_tone()
            raw = None
            if self._persona_tpl:
                raw = _pick_template(self._persona_tpl, tone)
            if not raw:
                if tone == "agro":
                    raw = "{user} lucky pull di sini dilarang. Pindahkan ke {channel} ya."
                elif tone == "sharp":
                    raw = "{user} ini bukan tempat lucky pull. Silakan pindah ke {channel}."
                else:
                    raw = "{user} jangan post lucky pull di sini. Mohon pindah ke {channel} ya."

            content = _render_notice(raw, message.author, self.redirect_id, self.mention_user)
            msg = await message.channel.send(content)
            await asyncio.sleep(max(1, int(self.notice_ttl)))
            await msg.delete()
        except Exception as e:
            log.debug("[lpa] notice failed: %r", e)

    @commands.Cog.listener("on_message")
    async def _on_message(self, message: discord.Message):
        try:
            if message.author.bot: return
            in_guard = str(message.channel.id) in self.guard_channels if self.guard_channels else False
            if not in_guard: return
        except Exception: return

        imgs = await self._collect_images(message)
        if not imgs: return

        if self.force_delete_test or self.strict_on_guard:
            label, conf = "lucky", 1.0
            log.warning("[lpa] TEST/STRICT fallback => lucky=1.0")
        else:
            label, conf = await self._classify(imgs)

        log.info("[lpa] classify: result=(%s, %.3f) thr=%.2f", label, conf, self.threshold)

        if self.fast_enable and label == "lucky" and conf >= self.fast_delete_thr and self.delete_on_guard:
            try:
                await message.delete()
                bus.mark_deleted(message.id)
                log.info("[lpa] fast-deleted a message in %s (reason=lucky pull)", message.channel.id)
            except Exception as e:
                log.warning("[lpa] fast-delete failed: %r", e)
            if self.notice_on_fast:
                await self._send_notice(message)
            return

        if label == "lucky" and conf >= self.threshold and self.delete_on_guard:
            try:
                await message.delete()
                bus.mark_deleted(message.id)
                log.info("[lpa] deleted a message in %s (reason=lucky pull)", message.channel.id)
            except Exception as e:
                log.warning("[lpa] delete failed: %r", e)
            await self._send_notice(message)

async def setup(bot: commands.Bot):
    await bot.add_cog(LuckyPullAuto(bot))
