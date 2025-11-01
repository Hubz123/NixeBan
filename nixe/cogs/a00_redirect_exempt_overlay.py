# nixe/cogs/a00_redirect_exempt_overlay.py
# Ensure Lucky Pull redirect channel(s) are never treated as guard/phish targets.
import os
from discord.ext import commands

def _csv_set(v):
    return {x.strip() for x in (v or "").split(",") if x and x.strip().isdigit()}

def _merge_list_env(key, extra_ids):
    cur = os.getenv(key, "") or ""
    s = _csv_set(cur)
    s |= set(extra_ids)
    os.environ[key] = ",".join(sorted(s))

def _remove_from_list_env(key, bad_ids):
    cur = os.getenv(key, "") or ""
    s = _csv_set(cur)
    s -= set(bad_ids)
    os.environ[key] = ",".join(sorted(s))

class RedirectExemptOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        cand = []
        for k in ("LPG_REDIRECT_CHANNEL_ID","LPA_REDIRECT_CHANNEL_ID","LUCKYPULL_REDIRECT_CHANNEL_ID"):
            v = (os.getenv(k,"") or "").strip()
            if v.isdigit():
                cand.append(v)
        self.redirect_ids = sorted({*cand})
        if not self.redirect_ids:
            return
        # Exempt redirect channel(s) from scans/guards
        _merge_list_env("SUS_ATTACH_IGNORE_CHANNELS", self.redirect_ids)
        _merge_list_env("PHASH_MATCH_SKIP_CHANNELS", self.redirect_ids)
        _merge_list_env("FIRST_TOUCHDOWN_BYPASS_CHANNELS", self.redirect_ids)
        # Ensure redirect not in guard lists
        for key in ("FIRST_TOUCHDOWN_CHANNELS","CRYPTO_CASINO_GUARD_CHANNELS",
                    "LPA_GUARD_CHANNELS","LPG_GUARD_CHANNELS","LUCKYPULL_GUARD_CHANNELS"):
            _remove_from_list_env(key, self.redirect_ids)

async def setup(bot: commands.Bot):
    add = getattr(bot, "add_cog")
    res = add(RedirectExemptOverlay(bot))
    import inspect
    if inspect.isawaitable(res):
        await res
