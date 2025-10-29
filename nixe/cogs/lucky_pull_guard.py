"""Lucky Pull Guard — clean canonical"""
from __future__ import annotations
import asyncio, json, logging, os, random
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
            log.debug("[lpg:debug] forced DEBUG via env")
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

def _load_yandere_persona():
    base = _load_runtime_env()
    path = os.getenv("YANDERE_TEMPLATES_PATH") or base.get("YANDERE_TEMPLATES_PATH") or "nixe/config/personas/yandere.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tones = data.get("groups") or data.get("tones") or {"soft": [], "agro": [], "sharp": []}
        if "tones" in data: tones = data["tones"]
        weights = (data.get("random_weights") or data.get("select",{}).get("weights")) or {"soft": 0.5, "agro": 0.3, "sharp": 0.2}
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
        self.timeout_ms = int(self.cfg.get("LUCKYPULL_GEM_TIMEOUT_MS", 20000))
        self.notice_ttl = int(self.cfg.get("LUCKYPULL_NOTICE_TTL", 20))
        try:
            import nixe.helpers.gemini_bridge as gb
            self.gb = gb
        except Exception as e:
            log.warning("[lpg] gemini bridge import failed: %r", e); self.gb = None

    def _redir_mention(self) -> str:
        rid = ''.join(ch for ch in self.redirect_id if ch.isdigit())
        return f"<#{rid}>" if rid else "#garem-moment"

    async def _classify(self, image_bytes: bytes) -> Tuple[str, float]:
        if not self.gb or not hasattr(self.gb, "classify_lucky_pull"):
            return ("other", 0.0)
        try:
            log.debug('[lpg] classify: calling gemini with timeout=%sms', self.timeout_ms)
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
                try: await message.delete()
                log.info('[lpg] deleted a message in %s (reason=lucky pull)', message.channel.id)
                except Exception: pass
            if self.mention_user:
                try:
                    mention = message.author.mention
                    redir = self._redir_mention()
                    note = await message.channel.send(_pick_yandere_line().format(mention=mention, redir=redir))
                    if self.notice_ttl>0: asyncio.create_task(self._later_delete(note, self.notice_ttl))
                except Exception: pass

async def setup(bot: commands.Bot):
    await bot.add_cog(LuckyPullGuard(bot))
