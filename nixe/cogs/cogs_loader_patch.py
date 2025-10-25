import logging
from discord.ext import commands
log = logging.getLogger(__name__)
FORBIDDEN_TOKENS = ("leina","satpambot")
def _forbidden(m:str)->bool:
    m=(m or "").lower(); return any(t in m for t in FORBIDDEN_TOKENS)
def apply_module_filter(mods):
    out=[]; 
    for m in mods:
        if _forbidden(m):
            try: log.info("⏭️  Skip provider due to policy: %s", m)
            except Exception: pass
            continue
        out.append(m)
    return out
async def setup(bot: commands.Bot): return
def legacy_setup(bot: commands.Bot): return
