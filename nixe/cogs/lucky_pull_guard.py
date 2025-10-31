"""Lucky Pull Guard — with Negative Hash Whitelist"""
from __future__ import annotations
import asyncio, json, logging, os, random, io, hashlib
from typing import Tuple, Optional, List
import discord
from discord.ext import commands

log = logging.getLogger("nixe.cogs.lucky_pull_guard")

# --- DEBUG booster via env ---
def _enable_debug_if_requested():
    try:
        flag = os.getenv("LPG_DEBUG", os.getenv("NIXE_LPG_VERBOSE", "0"))
        if str(flag).lower() in ("1","true","yes","y","on"):
            log.setLevel(logging.DEBUG)
            logging.getLogger(__name__).setLevel(logging.DEBUG)
    except Exception:
        pass

_enable_debug_if_requested()

def _load_runtime_env() -> dict:
    path = os.getenv("RUNTIME_ENV_PATH") or "nixe/config/runtime_env.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _coerce_list(v) -> List[str]:
    if isinstance(v, list): return [str(x) for x in v]
    if isinstance(v, str):  return [s.strip() for s in v.split(",") if s.strip()]
    return []

def _bool(v, default=True) -> bool:
    if v is None: return default
    s = str(v).strip().lower()
    return s in ("1","true","yes","on")

# --- lightweight hashes (no external deps) ---
try:
    from nixe.helpers.ahash import average_hash_bytes as _ahash_bytes
except Exception:
    _ahash_bytes = None

def _ahash_hex(b: bytes) -> Optional[str]:
    try:
        if _ahash_bytes:
            return _ahash_bytes(b, 8)
        # tiny fallback: same algorithm inline
        from PIL import Image
        import numpy as np
        im = Image.open(io.BytesIO(b)).convert("L").resize((8, 8))
        arr = np.asarray(im, dtype=np.float32)
        avg = float(arr.mean())
        bits = (arr >= avg).astype("uint8").flatten()
        v=0; out=[]
        for i,bit in enumerate(bits):
            v=(v<<1)|int(bit)
            if i%4==3: out.append(format(v,'x')); v=0
        if len(bits)%4!=0: out.append(format(v,'x'))
        return ''.join(out)
    except Exception:
        return None

def _dhash_hex(b: bytes) -> Optional[str]:
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(b)).convert("L").resize((9, 8))
        px = list(im.getdata()); w, h = im.size
        bits = []
        for y in range(h):
            row = [px[y*w+x] for x in range(w)]
            for x in range(w-1):
                bits.append(1 if row[x] < row[x+1] else 0)
        v=0; out=[]
        for i,bit in enumerate(bits):
            v=(v<<1)|int(bit)
            if i%4==3: out.append(format(v,'x')); v=0
        if len(bits)%4!=0: out.append(format(v,'x'))
        return ''.join(out)
    except Exception:
        return None

def _hex_to_int(h: str) -> int:
    try:
        return int(h.strip().lower().replace("0x",""), 16)
    except Exception:
        return -1

def _hamming_sim_hex(a: str, b: str, bits: int = 64) -> float:
    try:
        x = _hex_to_int(a) ^ _hex_to_int(b)
        # count bits
        cnt = 0
        while x:
            x &= x - 1
            cnt += 1
        dist = cnt
        return max(0.0, 1.0 - dist / float(bits))
    except Exception:
        return 0.0

def _load_neg_list_from_file(path: str) -> List[tuple[str,str]]:
    out = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"): continue
                if ":" in s:
                    t, v = s.split(":", 1)
                    t = t.strip().lower(); v = v.strip().lower()
                    if t in ("ahash","dhash","sha256"):
                        out.append((t, v))
    except Exception:
        pass
    return out

def _neglist(cfg: dict) -> tuple[list[str], list[str], list[str], float]:
    ahs = _coerce_list(os.getenv("LPG_NEG_AHASHES") or cfg.get("LPG_NEG_AHASHES"))
    dhs = _coerce_list(os.getenv("LPG_NEG_DHASHES") or cfg.get("LPG_NEG_DHASHES"))
    shs = _coerce_list(os.getenv("LPG_NEG_SHA256")  or cfg.get("LPG_NEG_SHA256"))
    path = os.getenv("LPG_NEG_FILE") or cfg.get("LPG_NEG_FILE") or "data/lpg_negative_hashes.txt"
    thr = float(os.getenv("LPG_NEG_MATCH", cfg.get("LPG_NEG_MATCH", 0.93)))
    for t, v in _load_neg_list_from_file(path):
        if t == "ahash": ahs.append(v)
        elif t == "dhash": dhs.append(v)
        elif t == "sha256": shs.append(v)
    return list(dict.fromkeys(ahs)), list(dict.fromkeys(dhs)), list(dict.fromkeys(shs)), thr

def _match_negative(b: bytes, ah: list[str], dh: list[str], sh: list[str], thr: float) -> bool:
    try:
        sha = hashlib.sha256(b).hexdigest()
        if sha in sh: return True
    except Exception: pass
    try:
        a = _ahash_hex(b)
        if a:
            for x in ah:
                if _hamming_sim_hex(a, x, 64) >= thr: return True
    except Exception: pass
    try:
        d = _dhash_hex(b)
        if d:
            for x in dh:
                if _hamming_sim_hex(d, x, 64) >= thr: return True
    except Exception: pass
    return False

# --- Gemini/Lucky helper
class _GemBridge:
    def __init__(self, cfg: dict):
        self.enable = _bool(cfg.get("LPG_GEMINI_ENABLE", cfg.get("GEMINI_ENABLE", True)), True)
        self.timeout_ms = int(cfg.get("LPG_GEM_TIMEOUT_MS", cfg.get("GEMINI_TIMEOUT_MS", 10000)))
    async def classify_lucky_pull(self, images: List[bytes], hints: str = "", timeout_ms: int = 10000) -> tuple[str, float]:
        if not self.enable: return ("other", 0.0)
        try:
            from nixe.helpers.lp_gemini_helper import classify_lucky_pull as _class
            return await _class(images, hints=hints, timeout_ms=min(timeout_ms, self.timeout_ms))
        except Exception:
            try:
                from nixe.helpers.gemini_bridge import classify_lucky_pull as _class2
                return await _class2(images, hints=hints, timeout_ms=min(timeout_ms, self.timeout_ms))
            except Exception:
                return ("other", 0.0)

def _load_yandere_persona():
    base = _load_runtime_env()
    path = os.getenv("YANDERE_TEMPLATES_PATH") or base.get("YANDERE_TEMPLATES_PATH") or "nixe/config/personas/yandere.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tones = data.get("groups") or data.get("tones") or {"soft": [], "agro": [], "sharp": []}
        weights = data.get("weights") or {"soft":0.6,"agro":0.3,"sharp":0.1}
        return tones, weights
    except Exception:
        return ({"soft": ["{mention} ke {redir}"], "agro": ["{mention} ke {redir}."], "sharp": ["{mention} → {redir}"]},
                {"soft":0.5,"agro":0.3,"sharp":0.2})

def _pick_yandere_line() -> str:
    base = _load_runtime_env()
    mode  = (os.getenv("YANDERE_TONE_MODE") or base.get("YANDERE_TONE_MODE") or "auto").strip().lower()
    fixed = (os.getenv("YANDERE_TONE_FIXED") or base.get("YANDERE_TONE_FIXED") or "soft").strip().lower()
    tones, weights = _load_yandere_persona()
    keys = ["soft","agro","sharp"]
    if mode=="fixed" and fixed in tones and tones[fixed]:
        tone = fixed
    else:
        w = [float((weights or {}).get(k,0)) for k in keys]
        if sum(w)<=0: w=[1,1,1]
        tone = random.choices(keys, weights=w, k=1)[0]
    templs = (tones.get(tone) or tones.get("soft") or ["{mention} ke {redir}"])
    return random.choice(templs)

class LuckyPullGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg = _load_runtime_env()
        self.guard_channels = set(_coerce_list(self.cfg.get("LUCKYPULL_GUARD_CHANNELS")))
        self.redirect_id = str(self.cfg.get("LUCKYPULL_REDIRECT_CHANNEL_ID") or self.cfg.get("LUCKYPULL_REDIRECT") or "0")
        self.delete_on_guard = _bool(self.cfg.get("LUCKYPULL_DELETE_ON_GUARD"), True)
        self.mention_user    = _bool(self.cfg.get("LUCKYPULL_MENTION_USER"), True)
        self.strict_on_guard = _bool(self.cfg.get("LUCKYPULL_STRICT_ON_GUARD"), True)
        self.threshold  = float(self.cfg.get("GEMINI_LUCKY_THRESHOLD", 0.87))
        self.timeout_ms = int(self.cfg.get("LPG_GEM_TIMEOUT_MS", 10000))
        self.notice_ttl = int(self.cfg.get("LUCKYPULL_NOTICE_TTL", 18))
        self.gb = _GemBridge(self.cfg)
        # --- NEW: negative whitelist hashes ---
        ah, dh, sh, thr = _neglist(self.cfg)
        self._neg_ahash = set([x.lower() for x in ah])
        self._neg_dhash = set([x.lower() for x in dh])
        self._neg_sha   = set([x.lower() for x in sh])
        self._neg_thr   = float(thr)
        if self._neg_ahash or self._neg_dhash or self._neg_sha:
            log.warning("[lpg] negative-whitelist active: ah=%d dh=%d sha=%d thr=%.2f",
                        len(self._neg_ahash), len(self._neg_dhash), len(self._neg_sha), self._neg_thr)

    def _redir_mention(self) -> str:
        try:
            cid = int(self.redirect_id or "0")
            return f"<#{{cid}}>" if cid else "channel yang benar"
        except Exception:
            return "channel yang benar"

    async def _classify(self, image_bytes: bytes) -> Tuple[str, float]:
        # Negative whitelist check BEFORE Gemini to avoid FP and save budget
        try:
            if _match_negative(image_bytes, list(self._neg_ahash), list(self._neg_dhash), list(self._neg_sha), self._neg_thr):
                log.info("[lpg] skip by whitelist (negative hash match)")
                return ("other", 0.0)
        except Exception:
            pass
        if not self.gb.enable:
            return ("other", 0.0)
        try:
            res = await self.gb.classify_lucky_pull([image_bytes], hints="guard", timeout_ms=self.timeout_ms)
            log.debug('[lpg] classify: result=%r', res)
            if isinstance(res, (list, tuple)) and len(res)>=2: return (str(res[0]), float(res[1]))
            if isinstance(res, dict): return (str(res.get("label","other")), float(res.get("conf",0.0)))
        except Exception: pass
        return ("other", 0.0)

    async def _later_delete(self, msg: discord.Message, seconds: int):
        try:
            await asyncio.sleep(max(1, seconds)); await msg.delete()
        except Exception: pass

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot: return
        if str(message.channel.id) not in self.guard_channels: return
        if not message.attachments: return
        img_bytes: Optional[bytes] = None
        for a in message.attachments:
            try:
                if (getattr(a,"content_type",None) and str(a.content_type).startswith("image/")) or img_bytes is None:
                    img_bytes = await a.read(); break
            except Exception: continue
        if not img_bytes: return
        label, conf = await self._classify(img_bytes)
        if label=="lucky" and conf>=self.threshold:
            if self.delete_on_guard:
                try:
                    await message.delete()
                    log.info('[lpg] deleted a message in %s (reason=lucky pull)', message.channel.id)
                except Exception:
                    pass
            if self.mention_user:
                try:
                    mention = message.author.mention
                    redir = self._redir_mention()
                    note = await message.channel.send(_pick_yandere_line().format(mention=mention, redir=redir))
                    if self.notice_ttl>0: asyncio.create_task(self._later_delete(note, self.notice_ttl))
                except Exception: pass

async def setup(bot: commands.Bot):
    await bot.add_cog(LuckyPullGuard(bot))
