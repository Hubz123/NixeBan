# -*- coding: utf-8 -*-
"""
a16_lpg_provider_enforcer_overlay
- Does NOT import heavy SDKs.
- No side effects at import time.
- Ensures sane LPG_* env defaults and flips provider order when Gemini is on cooldown.
"""

import os, time, logging
from discord.ext import commands, tasks

LOG = logging.getLogger(__name__)

def _getenv(k, d=None):
    v = os.getenv(k)
    return v if (v is not None and v != "") else d

def _setdefault(k, v):
    if _getenv(k) is None:
        os.environ[k] = str(v)
        return True
    return False

def _ensure_float_env(name, default):
    try:
        float(str(_getenv(name, default)))
    except Exception:
        os.environ[name] = str(default)
        LOG.warning("[lpg-enforcer] fixed %s to default=%s", name, default)

def _gemini_cooldown_until():
    # Keep in sync with gemini_bridge cooldown file path if possible
    path = os.path.join(os.getenv("TEMP", "/tmp"), "lpg_gemini_429.cooldown")
    try:
        with open(path, "r") as f:
            return float(f.read().strip() or "0")
    except Exception:
        return 0.0

class LPGProviderEnforcer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_order = None
        # minimal defaults so other modules never crash
        _setdefault("LPG_ENABLE", "1")
        _setdefault("LPG_IMG_FORCE_JPEG", "1")
        _setdefault("LPG_IMG_MAX_SIDE", "1280")
        _setdefault("LPG_IMG_TARGET_KB", "1500")
        _setdefault("LPG_CONF_EPSILON", "0.03")
        _setdefault("LPG_GEM_THRESHOLD", "0.50")
        _setdefault("LPG_GROQ_THRESHOLD", "0.50")
        _setdefault("LPG_GROQ_MODELS",
                    "meta-llama/llama-4-scout-17b-16e-instruct,meta-llama/llama-4-maverick-17b-128e-instruct")
        _setdefault("LPG_PROVIDER_ORDER", _getenv("LPG_PROVIDER_ORDER", "gemini,groq"))

        # numeric sanity
        _ensure_float_env("LPG_CONF_EPSILON", 0.03)
        _ensure_float_env("LPG_GEM_THRESHOLD", 0.50)
        _ensure_float_env("LPG_GROQ_THRESHOLD", 0.50)

        # one-shot enforce now, then start loop
        self._enforce()
        try:
            self.enforce_loop.start()
        except Exception:
            LOG.exception("[lpg-enforcer] failed to start loop")

    def cog_unload(self):
        try:
            self.enforce_loop.cancel()
        except Exception:
            pass

    @tasks.loop(seconds=90)
    async def enforce_loop(self):
        self._enforce()

    def _enforce(self):
        until = _gemini_cooldown_until()
        now = time.time()
        base_order = _getenv("LPG_PROVIDER_ORDER", "gemini,groq")
        order = base_order
        if until > now:
            # While on cooldown, force Groq first
            order = "groq,gemini"

        if order != os.getenv("LPG_PROVIDER_ORDER"):
            os.environ["LPG_PROVIDER_ORDER"] = order
            LOG.warning("[lpg-enforcer] provider order -> %s (cooldown=%ss)", order, int(max(0, until-now)))
        elif order != self._last_order:
            LOG.info("[lpg-enforcer] provider order %s (cooldown=%ss)", order, int(max(0, until-now)))
        self._last_order = order

        # Soft diagnostics (once)
        for k in ("GEMINI_API_KEY", "GROQ_API_KEY"):
            LOG.info("[lpg-enforcer] %s=%s", k, "OK" if bool(_getenv(k)) else "MISSING")


def setup(bot):
    bot.add_cog(LPGProviderEnforcer(bot))
