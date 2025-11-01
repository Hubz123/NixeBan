# nixe/cogs/lucky_pull_auto.py — fix {channel} placeholder + remove extra pre-delay
import os, time, json, random, re, logging, asyncio, discord
from typing import Dict, List, Optional, Tuple
from discord.ext import commands

_log = logging.getLogger(__name__)

def _getenv(k,d=""): return os.getenv(k,d)
def _csv(v): return [x.strip() for x in (v or "").split(",") if x.strip()]

def _parse_float(v, default):
    try: return float(str(v))
    except Exception: return default

def _resolve_threshold(default=0.85):
    for k in ("LPA_THRESHOLD_DELETE","GEMINI_LUCKY_THRESHOLD","LPG_LUCKY_THRESHOLD","GROQ_LUCKY_THRESHOLD","LPG_THRESHOLD_DELETE"):
        val = os.getenv(k)
        if val is not None:
            try: return float(val)
            except Exception: pass
    return default

def _expand_vars(text: str, author: discord.Member, channel: discord.abc.GuildChannel)->str:
    """Replace placeholders for user/channel safely."""
    if not text: return text
    out = text
    user_mention = author.mention if author else "@user"
    chan_mention = getattr(channel, "mention", "#channel")
    chan_name = getattr(channel, "name", "channel")
    parent = getattr(channel, "parent", None)
    parent_mention = getattr(parent, "mention", chan_mention) if parent else chan_mention

    # user
    out = re.sub(r"\{\{\s*user\s*\}\}|\{\s*user\s*\}|<\s*user\s*>|\$user|\$USER|\{USER\}", user_mention, out, flags=re.I)
    # channel
    out = re.sub(r"\{\{\s*channel\s*\}\}|\{\s*channel\s*\}|\$channel|\$CHANNEL|\{CHANNEL\}", chan_mention, out, flags=re.I)
    out = re.sub(r"\{\{\s*channel_name\s*\}\}|\{\s*channel_name\s*\}", chan_name, out, flags=re.I)
    # parent (for threads)
    out = re.sub(r"\{\{\s*parent\s*\}\}|\{\s*parent\s*\}|\{PARENT\}", parent_mention, out, flags=re.I)
    return out.strip()

def _flatten_yandere(obj) -> Dict[str, List[str]]:
    buckets = {"soft": [], "agro": [], "sharp": []}
    def put(tone, arr):
        if not isinstance(arr, list): return
        for s in arr:
            s = (s or "").strip()
            if not s or s.lower() in {"user","username","name"}: continue
            buckets.setdefault(tone, []).append(s)
    try:
        if isinstance(obj, list):
            put("soft", obj)
        elif isinstance(obj, dict):
            for key in ("lucky_pull","lucky","gacha","responses"):
                if key in obj and isinstance(obj[key], (list, dict)):
                    sub = _flatten_yandere(obj[key])
                    for k,v in sub.items(): buckets.setdefault(k, []).extend(v)
            for tone_key in ("soft","agro","sharp"):
                put(tone_key, obj.get(tone_key))
    except Exception:
        pass
    for k in list(buckets.keys()):
        seen=set(); ded=[]
        for s in buckets[k]:
            if s not in seen: ded.append(s); seen.add(s)
        buckets[k]=ded
    return buckets

def _load_persona_lines(path: str) -> Dict[str, List[str]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        root = obj
        if isinstance(obj, dict):
            for key in ("yandere","YANDERE","persona","PERSONA","pool","POOL"):
                if key in obj and isinstance(obj[key], (dict, list)):
                    root = obj[key]; break
        return _flatten_yandere(root)
    except Exception:
        return {"soft": [], "agro": [], "sharp": []}

class LuckyPullAuto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot=bot
        self.enabled=_getenv("LPA_ENABLE","1")=="1"
        self.delete_on_match=_getenv("LPA_DELETE_ON_MATCH","1")=="1"
        self.guard=set(_csv(_getenv("LPA_GUARD_CHANNELS","")))
        self.thr=_resolve_threshold(0.85)
        self.cool=int(_getenv("LPA_COOLDOWN_SEC","15") or 15)
        self.exec_mode=_getenv("LPA_EXECUTION_MODE","provider_first")
        self.defer=_getenv("LPA_DEFER_IF_PROVIDER_DOWN","1")=="1"
        self.order=_getenv("LPA_PROVIDER_ORDER","gemini,groq")
        self.kw_gate=_getenv("LPA_REQUIRE_TEXT_KEYWORD","0")=="1"

        # Persona
        self.persona_on = _getenv("LPG_PERSONA_ENABLE","1")=="1"
        self.persona_path = _getenv("PERSONA_PROFILE_PATH", _getenv("YANDERE_TEMPLATE_PATH","nixe/config/personas/yandere.json"))
        self._lines = _load_persona_lines(self.persona_path) if self.persona_on else {"soft": [],"agro":[],"sharp":[]}
        self._tone_cycle=["soft","agro","sharp"]; self._tone_idx=0

        # Providers
        self.BR=None; self.H=None
        try:
            from nixe.helpers import lpa_provider_bridge as BR; self.BR=BR
        except Exception: pass
        try:
            from nixe.helpers import lpa_heuristics as H; self.H=H
        except Exception: pass

        # Startup wait (>10s), no per-message extra delay
        try:
            self._startup_wait_sec = max(0, int(_getenv("LPA_STARTUP_WAIT_SEC","12") or "12"))
        except Exception:
            self._startup_wait_sec = 12

        # Non‑blocking provider controls — allow up to 15s provider time
        self._provider_timeout_ms = int(_getenv("LPA_PROVIDER_TIMEOUT_MS","15000") or "15000")
        self._provider_conc = max(1, int(_getenv("LPA_PROVIDER_CONCURRENCY","1") or "1"))
        self._sem = asyncio.Semaphore(self._provider_conc)

        self._t={}
        self._ready_gate_until = time.monotonic() + 999999  # updated on_ready
        _log.setLevel(logging.INFO)
        _log.propagate = True

    @commands.Cog.listener()
    async def on_ready(self): 
        self._ready_gate_until = time.monotonic() + float(self._startup_wait_sec)

    def _in(self, ch) -> bool:
        if not self.guard: return True
        try:
            chid = str(getattr(ch, "id", ""))
            parent_id = str(getattr(getattr(ch, "parent", None), "id", ""))
            return (chid in self.guard) or (parent_id and parent_id in self.guard)
        except Exception:
            return False

    def _ok(self, ch, au):
        now=time.time(); k=(ch,au); last=self._t.get(k,0.0)
        if now-last<self.cool: return False
        self._t[k]=now; return True

    def _collect_text(self, m: discord.Message)->str:
        parts=[m.content or ""]
        for e in m.embeds:
            if e.title: parts.append(e.title)
            if e.description: parts.append(e.description)
            if e.url: parts.append(e.url)
            if e.footer and e.footer.text: parts.append(e.footer.text)
            for f in getattr(e, "fields", []) or []:
                parts.append(f.name or ""); parts.append(f.value or "")
        for a in m.attachments:
            if a.filename: parts.append(a.filename)
        return "\n".join(parts).strip()

    async def _first_image_bytes(self, m: discord.Message):
        for a in m.attachments:
            ct = (getattr(a, "content_type", None) or "").lower()
            name = (a.filename or "").lower()
            looks_img = ct.startswith("image/") or name.endswith((".png",".jpg",".jpeg",".webp",".gif",".bmp"))
            if looks_img:
                try: return await a.read()
                except Exception: continue
        return None

    async def _provider_call_to_thread(self, func, *args):
        """Run blocking provider fn in thread with timeout to avoid heartbeat blocking."""
        try:
            timeout = max(0.3, self._provider_timeout_ms/1000.0)
            return await asyncio.wait_for(asyncio.to_thread(func, *args), timeout=timeout)
        except asyncio.TimeoutError:
            return (None, "timeout")
        except Exception:
            return (None, "provider_err")

    async def _classify(self, img_bytes: Optional[bytes], text: str) -> Tuple[Optional[float], str]:
        if not self.BR:
            return None, "no_bridge"
        if img_bytes:
            score, via = await self._provider_call_to_thread(self.BR.classify_with_image_bytes, img_bytes, self.order)
            if isinstance(score, float): return score, via
        score, via = await self._provider_call_to_thread(self.BR.classify, text, self.order)
        if isinstance(score, float): return score, via
        return None, via

    def _pick_persona_line(self, author: discord.Member, channel: discord.abc.GuildChannel)->str:
        mp = self._lines or {}
        for _ in range(3):
            tone=self._tone_cycle[self._tone_idx % len(self._tone_cycle)]
            self._tone_idx=(self._tone_idx+1)%len(self._tone_cycle)
            arr=mp.get(tone) or []
            if arr:
                raw = random.choice(arr)
                line = _expand_vars(raw, author, channel)
                if line: return line
        any_lines=[s for v in mp.values() for s in (v or [])]
        return _expand_vars(random.choice(any_lines), author, channel) if any_lines else ""

    async def on_message_inner(self, m: discord.Message):
        # Startup gate only
        if time.monotonic() < self._ready_gate_until:
            return

        text=self._collect_text(m)

        async with self._sem:
            img_bytes = await self._first_image_bytes(m) if m.attachments else None
            prob, via = await self._classify(img_bytes, text)

        if prob is None:
            _log.info(f"[lpa] classify: result=(deferred, --) thr={self.thr:.2f} via={via}")
            return

        label = "lucky" if prob >= self.thr else "not_lucky"
        _log.info(f"[lpa] classify: result=({label}, {prob:.3f}) thr={self.thr:.2f} via={via}")

        if self.kw_gate and not m.attachments:
            if self.H:
                try:
                    _, kw, _ = self.H.score_text_basic(text)
                    if kw == 0: return
                except Exception:
                    return

        if prob >= self.thr and self.delete_on_match:
            try:
                await m.delete()
                _log.info(f"[lpa] fast-deleted a message in {m.channel.id} (reason=lucky pull)")
            except Exception:
                return
            if self.persona_on:
                line = self._pick_persona_line(m.author, m.channel)
                if line:
                    try: await m.channel.send(line)
                    except Exception: pass

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if not self.enabled or not m.guild or m.author.bot: return
        if not self._in(m.channel): return
        if not self._ok(m.channel.id, m.author.id): return
        await self.on_message_inner(m)

async def setup(bot: commands.Bot):
    await bot.add_cog(LuckyPullAuto(bot))
