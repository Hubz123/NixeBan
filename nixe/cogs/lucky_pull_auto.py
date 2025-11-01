# nixe/cogs/lucky_pull_auto.py — Silent provider-first delete + yandere reply only
import os, time, json, random, discord
from typing import Optional, Dict, List
from discord.ext import commands

def _getenv(k,d=""): return os.getenv(k,d)
def _csv(v): return [x.strip() for x in (v or "").split(",") if x.strip()]

def _load_yandere(path: str) -> Dict[str, List[str]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
            if isinstance(obj, dict):
                # keep only lists of strings
                return {k: [s for s in v if isinstance(s,str)] for k,v in obj.items() if isinstance(v, list)}
    except Exception:
        pass
    # builtin fallback (short and safe)
    return {
        "soft": [
            "Hush, no gambling pics here~ Aku hapus ya ♥",
            "Ssst, simpan lucky pull-mu di tempat yang benar, oke?",
        ],
        "agro": [
            "Heh—lucky pull di sini? Hapus.",
            "Jangan coba-coba pamer gacha di sini. Gone.",
        ],
        "sharp": [
            "Lucky pull terdeteksi. Aku bersihkan. Lain kali, tempatkan di channel yang benar.",
            "Tidak ada lucky pull di sini. Selesai."
        ]
    }

class LuckyPullAuto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot=bot
        self.enabled=_getenv("LPA_ENABLE","1")=="1"
        self.delete_on_match=_getenv("LPA_DELETE_ON_MATCH","1")=="1"
        self.guard=set(_csv(_getenv("LPA_GUARD_CHANNELS","")))
        self.thr=float(_getenv("LPA_THRESHOLD_DELETE","0.85") or 0.85)
        self.cool=int(_getenv("LPA_COOLDOWN_SEC","15") or 15)
        self.exec_mode=_getenv("LPA_EXECUTION_MODE","provider_first")
        self.defer=_getenv("LPA_DEFER_IF_PROVIDER_DOWN","1")=="1"
        self.order=_getenv("LPA_PROVIDER_ORDER","gemini,groq")
        self.kw_gate=_getenv("LPA_REQUIRE_TEXT_KEYWORD","0")=="1"

        # yandere templates
        self.yandere_path = _getenv("YANDERE_TEMPLATE_PATH", "nixe/config/yandere.json")
        self._yandere = _load_yandere(self.yandere_path)
        self._tone_cycle = ["soft","agro","sharp"]
        self._tone_idx = 0

        # Optional bridges
        self.BR=None; self.H=None
        try:
            from nixe.helpers import lpa_provider_bridge as BR; self.BR=BR
        except Exception: pass
        try:
            from nixe.helpers import lpa_heuristics as H; self.H=H
        except Exception: pass

        self._t={}

    def _in(self, ch): return True if not self.guard else str(ch.id) in self.guard
    def _ok(self, ch, au):
        now=time.time(); k=(ch,au); last=self._t.get(k,0.0)
        if now-last<self.cool: return False
        self._t[k]=now; return True

    def _collect(self, m: discord.Message)->str:
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

    def _kw(self, text:str)->int:
        if not self.H: return 0
        try:
            _,kw,_=self.H.score_text_basic(text); return kw
        except Exception:
            return 0

    def _pick_yandere(self)->str:
        # rotate tone to add variety; if tone missing, fallback to any
        if not self._yandere: return "Lucky pull detected and removed."
        for _ in range(3):
            tone = self._tone_cycle[self._tone_idx % len(self._tone_cycle)]
            self._tone_idx = (self._tone_idx + 1) % len(self._tone_cycle)
            arr = self._yandere.get(tone) or []
            if arr:
                return random.choice(arr)
        # fallback any
        all_lines = [s for v in self._yandere.values() for s in (v or []) if isinstance(v, list)]
        return random.choice(all_lines) if all_lines else "Lucky pull detected and removed."

    async def on_message_inner(self, m: discord.Message):
        text=self._collect(m)

        prob,reason=(None,"no_bridge")
        if self.BR:
            try:
                prob,reason=self.BR.classify(text, self.order)
            except Exception:
                prob,reason=(None,"provider_err")

        if prob is None:
            if self.defer:
                # silently defer
                pass
            return

        if self.kw_gate and self._kw(text)==0:
            return  # silently skip

        if prob>=self.thr and self.delete_on_match:
            try:
                await m.delete()
            except Exception:
                return  # stay silent on failure
            # Send exactly one yandere line (no embeds, no logs)
            try:
                await m.channel.send(self._pick_yandere())
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if not self.enabled or not m.guild or m.author.bot: return
        if not self._in(m.channel): return
        if not self._ok(m.channel.id, m.author.id): return
        await self.on_message_inner(m)

async def setup(bot: commands.Bot):
    await bot.add_cog(LuckyPullAuto(bot))
