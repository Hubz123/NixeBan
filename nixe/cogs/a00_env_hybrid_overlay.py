# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, logging
from pathlib import Path
from typing import Any, Dict
from discord.ext import commands

log = logging.getLogger("nixe.cogs.a00_env_hybrid_overlay")

# Kunci yang boleh diexport dari nixe/config/runtime_env.json ke os.environ
PREFERRED_KEYS = [
    # Phish (Gemini)
    "PHISH_GEMINI_ENABLE","PHISH_GEMINI_THRESHOLD","PHISH_GEMINI_MAX_IMAGES",
    "PHISH_GEMINI_MAX_LATENCY_MS","PHISH_GEMINI_MODEL","PHISH_GEMINI_HINTS",

    # Lucky pull + Gemini
    "GEMINI_LUCKY_THRESHOLD","LUCKYPULL_GEMINI_THRESHOLD","GEMINI_LUCKY_HINTS",
    "GEMINI_MODEL","GEMINI_API_KEY","GOOGLE_API_KEY",

    # Lucky pull routing
    "LPA_GUARD_CHANNELS","LUCKYPULL_GUARD_CHANNELS","LPG_GUARD_CHANNELS",
    "LPA_REDIRECT_CHANNEL_ID","LUCKYPULL_REDIRECT_CHANNEL_ID","LPG_REDIRECT_CHANNEL_ID",
    "LPA_DELETE_ON_GUARD","LUCKYPULL_DELETE_ON_GUARD","LPG_DELETE_ON_GUARD",
    "LPA_MENTION_USER","LUCKYPULL_MENTION_USER","LPG_MENTION_USER",
    "LPA_STRICT_ON_GUARD","LUCKYPULL_STRICT_ON_GUARD","LPG_STRICT_ON_GUARD",
    "LPA_FORCE_DELETE_TEST","LPG_FORCE_DELETE_TEST",
    "LPA_NOTICE_ENABLE","LUCKYPULL_NOTICE_ENABLE","LPA_NOTICE_TTL","LUCKYPULL_NOTICE_TTL",
    "YANDERE_TONE_MODE","YANDERE_TONE_FIXED","YANDERE_TEMPLATES_PATH","YANDERE_RANDOM_WEIGHTS",

    # >>> Suspicious attachment hardener (WAJIB untuk phishing ketat)
    "SUS_ATTACH_HARDENER_ENABLE","SUS_ATTACH_ENABLE",
    "SUS_ATTACH_DELETE_THRESHOLD","SUS_ATTACH_MAX_BYTES",
    "SUS_ATTACH_LOG_VERBOSE","SUS_ATTACH_CONTENT_SCAN_ENABLE",
    "SUS_ATTACH_GEMINI_ENABLE","SUS_ATTACH_GEMINI_THRESHOLD",
    "SUS_ATTACH_GEM_TIMEOUT_MS","SUS_ATTACH_GEMINI_HINTS",
    "SUS_ATTACH_IGNORE_CHANNELS","SUS_ATTACH_ALWAYS_GEM",

    # pHash / Channels
    "PHASH_DB_THREAD_ID","PHASH_DB_MESSAGE_ID","PHASH_IMAGEPHISH_THREAD_ID",
    "NIXE_PHISH_LOG_CHAN_ID","LOG_CHANNEL_ID",

    # Misc logging
    "LOG_LEVEL","COGS_DEBUG_LIST","GRPC_VERBOSITY","GLOG_minloglevel","TF_CPP_MIN_LOG_LEVEL",
]

def _load_json() -> Dict[str, Any]:
    for p in (
        Path("nixe/config/runtime_env.json"),
        Path.cwd() / "nixe" / "config" / "runtime_env.json",
        Path(__file__).resolve().parent.parent / "config" / "runtime_env.json",
    ):
        try:
            if p.exists():
                return json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("[env-hybrid] failed reading %s: %r", p, e)
    return {}

def _coerce(v: Any) -> str:
    if isinstance(v, (list, tuple, set)): return ",".join(str(x) for x in v)
    if isinstance(v, dict): return json.dumps(v, ensure_ascii=False)
    return str(v)

class EnvHybridOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        data = _load_json()
        applied = {}
        for k in PREFERRED_KEYS:
            if os.environ.get(k) in (None, "") and k in data:
                os.environ[k] = _coerce(data[k]); applied[k] = os.environ[k]

        if applied or data:
            preview_keys = [
                "PHISH_GEMINI_THRESHOLD","GEMINI_LUCKY_THRESHOLD",
                "PHASH_DB_THREAD_ID","PHASH_IMAGEPHISH_THREAD_ID",
                # >>> pastikan SUS_* ikut tampil di preview
                "SUS_ATTACH_GEMINI_THRESHOLD","SUS_ATTACH_ALWAYS_GEM",
                "SUS_ATTACH_CONTENT_SCAN_ENABLE"
            ]
            pr = {k: applied.get(k, os.environ.get(k,"")) for k in preview_keys if (k in applied or os.environ.get(k))}
            log.warning("[env-hybrid] exported %d keys from runtime_env.json; preview=%s", len(applied), pr)

async def setup(bot: commands.Bot):
    await bot.add_cog(EnvHybridOverlay(bot))
