
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, asyncio, logging, random
from pathlib import Path
import discord
from discord.ext import commands

from nixe.helpers.lp_patterns import compile_from_env, match_any

LOGGER = logging.getLogger(__name__)

# ---------- ENV HELPERS ----------
def _load_json_env():
    try:
        envp = Path(__file__).resolve().parents[1] / "config" / "runtime_env.json"
        return json.loads(envp.read_text(encoding="utf-8"))
    except Exception:
        return {}
_JSON = _load_json_env()

def _as_bool(v: str) -> bool:
    return str(v).strip().lower() in ("1","true","on","yes")

def _get_env(key: str, default: str = "0") -> str:
    override = _as_bool(_JSON.get("NIXE_ENV_OVERRIDE", os.getenv("NIXE_ENV_OVERRIDE","0")))
    if override:
        v = _JSON.get(key, None)
        if v is not None:
            return str(v)
        return os.getenv(key, default)
    else:
        v = os.getenv(key, None)
        if v is not None:
            return v
        return str(_JSON.get(key, default))

# Core toggles
DELETE_ON_GUARD = _as_bool(_get_env("LUCKYPULL_DELETE_ON_GUARD","1"))
MENTION_ON_GUARD = _as_bool(_get_env("LUCKYPULL_MENTION","1"))
DEBUG = _as_bool(_get_env("LUCKYPULL_DEBUG","0"))
MAX_LAT_MS = int((_get_env("LUCKYPULL_MAX_LATENCY_MS","800") or "800").strip())

# Detection policy
HEUR_MODE = (_get_env("LUCKYPULL_HEUR_MODE","soft") or "soft").strip().lower()
USE_GEMINI = _as_bool(_get_env("LUCKYPULL_GEMINI_ENABLE","1"))
RAW_PAT = _get_env("LUCKYPULL_PATTERN","")
PATS = compile_from_env(RAW_PAT)

# Persona toggles
PERSONA = (_get_env("LUCKYPULL_PERSONA","yandere") or "yandere").strip().lower()
TONE_CFG = (_get_env("LUCKYPULL_TONE","agro") or "agro").strip().lower()   # 'soft' | 'agro' | 'sharp' | 'random'
TONE_WEIGHTS_RAW = (_get_env("LUCKYPULL_TONE_WEIGHTS","soft:1,agro:1,sharp:1") or "soft:1,agro:1,sharp:1").strip()
TONE_STICKY = (_get_env("LUCKYPULL_TONE_STICKY","none") or "none").strip().lower() # 'none' | 'author' | 'channel'
TPL_SOFT  = _get_env("LUCKYPULL_PERSONA_TPL_SOFT",  "")
TPL_AGRO  = _get_env("LUCKYPULL_PERSONA_TPL_AGRO",  "")
TPL_SHARP = _get_env("LUCKYPULL_PERSONA_TPL_SHARP", "")

def _parse_tone_weights(raw: str):
    weights = {"soft":1.0, "agro":1.0, "sharp":1.0}
    try:
        for tok in raw.split(","):
            tok = tok.strip()
            if not tok: continue
            if ":" in tok:
                k, v = tok.split(":", 1)
                k = k.strip().lower()
                v = float(v.strip())
                if k in weights and v > 0:
                    weights[k] = v
    except Exception:
        pass
    return weights

TONE_WEIGHTS = _parse_tone_weights(TONE_WEIGHTS_RAW)

def _resolve_tone(message: discord.Message) -> str:
    allowed = ("soft","agro","sharp")
    if TONE_CFG in allowed:
        return TONE_CFG
    if TONE_CFG in ("random","rand","shuffle","any","*"):
        # sticky seeding for consistent randomness per author/channel if desired
        seed = None
        try:
            if TONE_STICKY == "author" and message and message.author:
                seed = int(getattr(message.author, "id", 0)) or None
            elif TONE_STICKY == "channel" and message and message.channel:
                seed = int(getattr(message.channel, "id", 0)) or None
        except Exception:
            seed = None
        rng = random.Random(seed)
        population = list(allowed)
        weights = [TONE_WEIGHTS.get(t,1.0) for t in population]
        try:
            choice = rng.choices(population=population, weights=weights, k=1)[0]
        except Exception:
            choice = rng.choice(population)
        return choice
    # fallback
    return "agro"

# ---------- OPTIONAL GEMINI ----------
async def _gemini_judge(message: discord.Message, timeout_ms: int) -> bool:
    if not USE_GEMINI:
        return False
    try:
        from nixe.helpers.lp_gemini_helper import is_lucky_pull as _judge
    except Exception:
        return False
    async def _run():
        try:
            try:
                dec, conf, *_ = _judge(None, threshold=0.65)
                return bool(dec) and float(conf or 0.0) >= 0.65
            except TypeError:
                return bool(_judge(None))
        except Exception:
            return False
    try:
        return await asyncio.wait_for(_run(), timeout=timeout_ms/1000.0)
    except Exception:
        return False

# ---------- HEURISTICS ----------
def _looks_like_image(att: discord.Attachment) -> bool:
    ct = (att.content_type or "").lower() if hasattr(att, "content_type") else ""
    if ct.startswith("image/"):
        return True
    name = (att.filename or "").lower()
    return any(name.endswith(ext) for ext in (".png",".jpg",".jpeg",".webp",".gif",".bmp",".heic",".heif"))

def _has_image(msg: discord.Message) -> bool:
    return any(_looks_like_image(a) for a in getattr(msg, "attachments", []) or [])

def _text_for_match(msg: discord.Message) -> str:
    base = (msg.content or "")
    try:
        names = " ".join([(a.filename or "") for a in (msg.attachments or [])])
        base = f"{base} {names}".strip()
    except Exception:
        pass    # ignore
    return base

# ---------- PERSONA ----------
def _persona_line(message: discord.Message, redirect_id: int) -> str:
    user_mention = message.author.mention if getattr(message, "author", None) else ""
    chan = f"<#{redirect_id}>"
    tone = _resolve_tone(message)

    if PERSONA == "yandere":
        # allow template override first
        if tone == "soft" and TPL_SOFT:
            return TPL_SOFT.format(u=user_mention, c=chan)
        if tone == "agro" and TPL_AGRO:
            return TPL_AGRO.format(u=user_mention, c=chan)
        if tone in ("sharp",) and TPL_SHARP:
            return TPL_SHARP.format(u=user_mention, c=chan)

        # defaults
        if tone == "soft":
            return f"{user_mention} jangan manja di sini... pindah ke {chan} ya~ aku liatin kamu, jangan bikin aku cemburu >_<"
        if tone == "sharp":
            return f"{user_mention} semua 'gacha bahagia' bukan buat di sini. Ke {chan}. Jangan ngeyel—aku benci diabaikan."
        # agro
        return f"{user_mention} ini bukan tempatnya. Pindah ke {chan}. Sekarang. Jangan bikin aku ulang ngomong 💢"

    # polite default
    return f"{user_mention} lucky pull pindah ke {chan} ya 🙏"

# ---------- ACTION ----------
async def _delete_and_mention(bot, message: discord.Message, redirect_id: int):
    # Permission check
    try:
        perms = message.channel.permissions_for(message.guild.me) if message.guild else None
        if perms and not perms.manage_messages:
            if MENTION_ON_GUARD:
                try:
                    await message.channel.send(_persona_line(message, redirect_id) + " (bot kurang izin hapus)", delete_after=15)
                except Exception:
                    pass
            if DEBUG: LOGGER.info("[lpg] skip-delete: missing Manage Messages in #%s", getattr(message.channel,"name",message.channel.id))
            return
    except Exception:
        pass
    # Delete fast
    try:
        await message.delete()
        if DEBUG: LOGGER.info("[lpg] deleted a message in %s", message.channel.id)
    except Exception as e:
        if DEBUG: LOGGER.info("[lpg] delete failed: %s", e)
    # Then speak
    if MENTION_ON_GUARD:
        try:
            await message.channel.send(_persona_line(message, redirect_id), delete_after=15)
        except Exception:
            pass

# ---------- COG ----------
class LuckyPullDeleteMentionEnforcer(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message or not getattr(message,"guild",None): return
        author = getattr(message, "author", None)
        if author and getattr(author, "bot", False): return
        if not DELETE_ON_GUARD: return

        try:
            allow = [s.strip() for s in (_get_env("LUCKYPULL_ALLOW_CHANNELS","") or "").split(",") if s.strip().isdigit()]
            if str(message.channel.id) in allow:
                if DEBUG: LOGGER.info("[lpg] skip: allow-list channel %s", message.channel.id)
                return

            guards = [s.strip() for s in (_get_env("LUCKYPULL_GUARD_CHANNELS","") or "").split(",") if s.strip().isdigit()]
            redirect_id = int((_get_env("LUCKYPULL_REDIRECT_CHANNEL_ID","0") or "0").strip())
            if not redirect_id: 
                if DEBUG: LOGGER.info("[lpg] skip: redirect_id=0")
                return
            ch_id = int(message.channel.id)
            if str(ch_id) not in guards:
                return
            if ch_id == redirect_id:
                return  # anti-loop

            text = _text_for_match(message)
            has_img = _has_image(message)
            matched = match_any(text, PATS)

            is_lp = False
            if HEUR_MODE == "off":
                is_lp = matched
            elif HEUR_MODE == "strict":
                is_lp = has_img and matched
            else:  # soft
                is_lp = has_img and matched

            if not is_lp and USE_GEMINI:
                is_lp = await _gemini_judge(message, MAX_LAT_MS)
                if DEBUG: LOGGER.info("[lpg] gem=%s (<=%sms) in #%s", is_lp, MAX_LAT_MS, ch_id)

            if DEBUG:
                LOGGER.info("[lpg] ch=%s img=%s matched=%s mode=%s tone=%s text='%s'",
                            ch_id, has_img, matched, HEUR_MODE, _resolve_tone(message), text[:80])

            if is_lp:
                await _delete_and_mention(self.bot, message, redirect_id)

        except Exception as e:
            if DEBUG: LOGGER.exception("[lpg] error: %s", e)

class LuckyPullGuard(LuckyPullDeleteMentionEnforcer):
    pass

async def setup(bot):
    if DEBUG:
        try: LOGGER.setLevel(logging.INFO)
        except Exception: pass
        LOGGER.info("[lpg] setup: mode=%s delete=%s mention=%s gem=%s maxlat=%sms guards=%s redir=%s tone=%s weights=%s sticky=%s",
                    HEUR_MODE, DELETE_ON_GUARD, MENTION_ON_GUARD, USE_GEMINI, MAX_LAT_MS,
                    _get_env("LUCKYPULL_GUARD_CHANNELS",""), _get_env("LUCKYPULL_REDIRECT_CHANNEL_ID","0"),
                    TONE_CFG, TONE_WEIGHTS, TONE_STICKY)
    if bot.get_cog("LuckyPullGuard") or bot.get_cog("LuckyPullDeleteMentionEnforcer"): return
    try:
        await bot.add_cog(LuckyPullDeleteMentionEnforcer(bot))
    except Exception:
        pass
