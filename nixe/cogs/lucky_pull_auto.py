# -*- coding: utf-8 -*-
from __future__ import annotations
import os, re, json, logging, asyncio, random
from typing import Iterable, Tuple, List, Optional, Any
from pathlib import Path
import discord
from discord.ext import commands

log = logging.getLogger("nixe.cogs.lucky_pull_auto")

_RUNTIME_JSON_CACHE: dict[str, Any] | None = None
_PERSONA_CACHE: dict[str, List[str]] | None = None

def _load_runtime_json() -> dict[str, Any]:
    global _RUNTIME_JSON_CACHE
    if _RUNTIME_JSON_CACHE is not None:
        return _RUNTIME_JSON_CACHE
    here = Path(__file__).resolve()
    for p in [here.parent.parent / "config" / "runtime_env.json",
              Path.cwd() / "nixe" / "config" / "runtime_env.json",
              Path("nixe/config/runtime_env.json")]:
        try:
            if p.exists():
                _RUNTIME_JSON_CACHE = json.loads(p.read_text(encoding="utf-8"))
                break
        except Exception:
            _RUNTIME_JSON_CACHE = {}
    return _RUNTIME_JSON_CACHE or {}

def _jget(keys: Iterable[str]):
    envj = _load_runtime_json()
    for k in keys:
        if k in envj:
            return envj[k]
    return None

def _env_get(*keys: str, default: Optional[str] = None) -> Optional[str]:
    for k in keys:
        v = os.getenv(k)
        if v not in (None, ""):
            return v
    vj = _jget(keys)
    if isinstance(vj, (str, int, float)):
        return str(vj)
    if isinstance(vj, (list, tuple)):
        return ",".join([str(x) for x in vj])
    return default

def _parse_id_list(s: str | Iterable[str]) -> List[str]:
    if isinstance(s, (list, tuple, set)):
        raw = [str(x) for x in s]
    else:
        raw = re.split(r"[,\\s;]+", str(s or ""))
    out = []
    seen = set()
    for x in raw:
        x = x.strip()
        if x.isdigit() and x not in seen:
            seen.add(x)
            out.append(x)
    return out

def _float_env(*keys: str, default: float = 0.0) -> float:
    v = _env_get(*keys, default=None)
    try:
        return float(v) if v is not None else default
    except Exception:
        return default

# -------- Gemini bridge --------
try:
    from nixe.helpers.gemini_bridge import classify_lucky_pull  # async
except Exception as e:
    log.warning("[lpa] failed to import gemini bridge: %r", e)
    async def classify_lucky_pull(images: Iterable[bytes], hints: str = "", timeout_ms: int = 10000):
        return "other", 0.0

# -------- Persona helpers --------
def _load_yandere_templates() -> dict[str, List[str]]:
    global _PERSONA_CACHE
    if _PERSONA_CACHE is not None:
        return _PERSONA_CACHE  # type: ignore[return-value]
    path = _env_get("YANDERE_TEMPLATES_PATH", default="nixe/config/personas/yandere.json") or "nixe/config/personas/yandere.json"
    try:
        p = Path(path)
        if not p.exists():
            # default templates (5 per tone)
            tpl = {
                "soft": [
                    "hei {mention}~ itu tempat yang salah ya. simpen hasil gacha-mu di {redir} saja, oke? 💙",
                    "ehe~ {mention}, mommy simpan dulu ya. lain kali di {redir} ya sayang ✨",
                    "{mention}… di sini bukan tempat pamer hasil pull. pindah ke {redir} ya ❤️",
                    "ini lucu sih—tapi salah tempat, {mention}. ayo ke {redir}~",
                    "sayang {mention}, aku hapus dulu ya. next time drop-nya ke {redir} 💫"
                ],
                "agro": [
                    "oi {mention}. pamer gacha di sini? salah channel. ke {redir} sana.",
                    "{mention}, baca nama channelnya. bukan buat lucky-pull. pindah ke {redir}.",
                    "hapus. {mention}, kirim ke {redir} kalau mau pamer.",
                    "{mention}… mau kuikat di {redir} atau gimana? next time di sana.",
                    "salah tempat lagi? {mention} ke {redir}. sekarang."
                ],
                "sharp": [
                    "{mention}, pelanggaran channel. konten gacha → {redir}. Pesan dihapus.",
                    "Notifikasi: unggahanmu dihapus. Gunakan {redir} untuk hasil pull, {mention}.",
                    "{mention}, compliance check: lucky-pull di {redir}. Ulangi dengan benar.",
                    "Kebijakan kanal berlaku. {mention} kirim di {redir}. Pesan sebelumnya dihapus.",
                    "Enforcement aktif. {mention}: arahkan konten gacha ke {redir}."
                ]
            }
            _PERSONA_CACHE = tpl  # type: ignore[assignment]
            return tpl
        data = json.loads(p.read_text(encoding="utf-8"))
        # normalize structure
        for k in ("soft","agro","sharp"):
            data.setdefault(k, [])
            if not isinstance(data[k], list):
                data[k] = []
        _PERSONA_CACHE = data  # type: ignore[assignment]
        return data
    except Exception as e:
        log.debug("[lpa] yandere templates load failed: %r", e)
        _PERSONA_CACHE = {"soft": [], "agro": [], "sharp": []}  # type: ignore[assignment]
        return _PERSONA_CACHE  # type: ignore[return-value]

def _pick_tone() -> str:
    mode = (_env_get("YANDERE_TONE_MODE", default="auto") or "auto").lower()
    if mode in ("soft","agro","sharp"):
        return mode
    if mode == "random":
        weights = _jget(["YANDERE_RANDOM_WEIGHTS"]) or {"soft":"0.5","agro":"0.3","sharp":"0.2"}
        try:
            ws = [float(weights.get("soft","0.5")), float(weights.get("agro","0.3")), float(weights.get("sharp","0.2"))]
            return random.choices(["soft","agro","sharp"], weights=ws, k=1)[0]
        except Exception:
            return random.choice(["soft","agro","sharp"])
    # auto == random with bias to soft
    return random.choices(["soft","agro","sharp"], weights=[0.6,0.25,0.15], k=1)[0]

def _format_notice(tone: str, author: discord.User|discord.Member, redirect_id: str) -> str:
    tpl = _load_yandere_templates().get(tone) or []
    if not tpl:
        tpl = ["{mention}, hapus ya. kirim di {redir}."]
    text = random.choice(tpl)
    mention = author.mention
    redir = f"<#{redirect_id}>" if redirect_id else "#lucky-pull"
    return text.format(mention=mention, redir=redir)

async def _send_notice(ch: discord.TextChannel, content: str, ttl: int):
    try:
        msg = await ch.send(content)
        if ttl > 0:
            async def _later(m): 
                try:
                    await asyncio.sleep(ttl)
                    await m.delete()
                except Exception: 
                    pass
            asyncio.create_task(_later(msg))
    except Exception as e:
        log.debug("[lpa] send notice failed: %r", e)

class LuckyPullAuto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        chs = _env_get("LPA_GUARD_CHANNELS","LUCKYPULL_GUARD_CHANNELS","LPG_GUARD_CHANNELS","GUARD_CHANNELS","LUCKYPULL_CHANNELS","") or ""
        self.guard_channels: List[str] = _parse_id_list(chs)
        self.redirect_id: str = _env_get("LPA_REDIRECT_CHANNEL_ID","LUCKYPULL_REDIRECT_CHANNEL_ID","LPG_REDIRECT_CHANNEL_ID","LUCKYPULL_REDIRECT","REDIRECT_CHANNEL_ID","") or ""
        self.delete_on_guard: bool = bool(int(_env_get("LPA_DELETE_ON_GUARD","LUCKYPULL_DELETE_ON_GUARD","LPG_DELETE_ON_GUARD","1")))
        self.mention_user: bool = bool(int(_env_get("LPA_MENTION_USER","LUCKYPULL_MENTION_USER","LPG_MENTION_USER","1")))
        self.strict_on_guard: bool = bool(int(_env_get("LPA_STRICT_ON_GUARD","LUCKYPULL_STRICT_ON_GUARD","LPG_STRICT_ON_GUARD","0")))
        self.force_delete_test: bool = bool(int(_env_get("LPA_FORCE_DELETE_TEST","LPG_FORCE_DELETE_TEST","0")))
        self.threshold = _float_env("GEMINI_LUCKY_THRESHOLD","LUCKYPULL_GEMINI_THRESHOLD", default=0.80)
        self.timeout_ms = int(float(_env_get("LUCKYPULL_GEM_TIMEOUT_MS","LPG_GEM_TIMEOUT_MS","GEMINI_TIMEOUT_MS","20000")))
        self.hints = _env_get("GEMINI_LUCKY_HINTS","LUCKYPULL_HINTS","") or "blue archive 10-pull results grid NEW!! star icons rainbow/gold beam character tiles"
        # Yandere notice
        self.notice_enable: bool = bool(int(_env_get("LPA_NOTICE_ENABLE","LUCKYPULL_NOTICE_ENABLE","1")))
        self.notice_ttl: int = int(float(_env_get("LPA_NOTICE_TTL","LUCKYPULL_NOTICE_TTL","20")))
        self.tone_mode: str = (_env_get("YANDERE_TONE_MODE", default="auto") or "auto")
        log.warning("[lpa:boot] guard=%s redirect=%s del=%s mention=%s thr=%.2f strict=%s test=%s",
            self.guard_channels, self.redirect_id, self.delete_on_guard, self.mention_user,
            self.threshold, self.strict_on_guard, self.force_delete_test)

    async def _collect_image(self, message: discord.Message):
        blobs = []
        for att in getattr(message, "attachments", []) or []:
            try:
                if isinstance(att, discord.Attachment):
                    b = await att.read()
                    if b:
                        blobs.append(b)
                        break
            except Exception:
                pass
        if blobs:
            return blobs
        for emb in getattr(message, "embeds", []) or []:
            try:
                url = ""
                if emb.image and emb.image.url:
                    url = emb.image.url
                elif emb.thumbnail and emb.thumbnail.url:
                    url = emb.thumbnail.url
                if url.startswith("http"):
                    try:
                        import aiohttp
                        async with aiohttp.ClientSession() as s:
                            async with s.get(url, timeout=10) as r:
                                if r.status == 200:
                                    blobs.append(await r.read())
                                    break
                    except Exception:
                        try:
                            import requests
                            import asyncio as _asyncio
                            data = await _asyncio.to_thread(lambda: requests.get(url, timeout=10).content)
                            if data:
                                blobs.append(data)
                                break
                        except Exception:
                            pass
            except Exception:
                pass
        return blobs

    async def _classify(self, blobs):
        try:
            return await classify_lucky_pull(blobs, hints=self.hints, timeout_ms=self.timeout_ms)
        except Exception as e:
            log.warning("[lpa] classify error: %r", e)
            return "other", 0.0

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

        log.info("[lpa] seen in guard: chan=%s(%s) att=%d embeds=%d",
                 message.channel.id, getattr(message.channel, "name", "?"),
                 len(getattr(message, "attachments", []) or []),
                 len(getattr(message, "embeds", []) or []))

        imgs = await self._collect_image(message)
        if not imgs:
            return

        if self.force_delete_test or self.strict_on_guard:
            label, conf = "lucky", 1.0
            log.warning("[lpa] TEST/STRICT fallback => lucky=1.0")
        else:
            label, conf = await self._classify(imgs)

        log.info("[lpa] classify: result=(%s, %.3f) thr=%.2f", label, conf, self.threshold)

        if label == "lucky" and conf >= self.threshold and self.delete_on_guard:
            try:
                await message.delete()
                log.info("[lpa] deleted a message in %s (reason=lucky pull)", message.channel.id)
            except Exception as e:
                log.warning("[lpa] delete failed: %r", e)

            # Yandere notice
            try:
                if self.notice_enable and isinstance(message.channel, discord.TextChannel):
                    tone = _pick_tone()
                    content = _format_notice(tone, message.author, self.redirect_id)
                    await _send_notice(message.channel, content, self.notice_ttl)
            except Exception as e:
                log.debug("[lpa] notice failed: %r", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(LuckyPullAuto(bot))
