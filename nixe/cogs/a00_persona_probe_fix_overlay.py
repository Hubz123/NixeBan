# -*- coding: utf-8 -*-
import logging, os
from discord.ext import commands

log = logging.getLogger("nixe.cogs.a00_persona_probe_fix_overlay")

def _get(k, *alts, default=None):
    for n in (k,)+alts:
        v = os.getenv(n)
        if v is not None and str(v) != "":
            return v
    return default

def _set_env(k, v):
    if v is not None:
        os.environ[k] = str(v)

class PersonaProbeFix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._done = False

    def _compute_persona(self):
        mode = _get("PERSONA_MODE", "PERSONA_ACTIVE", "PERSONA", "ACTIVE_PERSONA", default="random")
        pool = _get("PERSONA_POOL", default="yandere")
        name = _get("PERSONA_DISPLAY_NAME", "PERSONA_NAME", default=f"Nixe ({mode.capitalize()} {pool})")
        profile = _get("PERSONA_PROFILE_PATH", default="nixe/config/personas/yandere.json")
        return mode, pool, name, profile

    def _sync_env_aliases(self, mode, pool, name, profile):
        for k, v in {
            "PERSONA": mode,
            "PERSONA_MODE": mode,
            "PERSONA_ACTIVE": mode,
            "ACTIVE_PERSONA": mode,
            "PERSONA_POOL": pool,
            "PERSONA_NAME": name,
            "PERSONA_DISPLAY_NAME": name,
            "PERSONA_PROFILE_PATH": profile
        }.items():
            _set_env(k, v)

    @commands.Cog.listener("on_ready")
    async def _on_ready(self):
        if self._done:
            return
        self._done = True
        mode, pool, name, profile = self._compute_persona()
        self._sync_env_aliases(mode, pool, name, profile)
        log.warning("[persona-probe] Active persona: %s", name)

async def setup(bot):
    await bot.add_cog(PersonaProbeFix(bot))
