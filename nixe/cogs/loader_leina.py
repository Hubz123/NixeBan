from __future__ import annotations
import logging, pkgutil, importlib, os
# Ensure dedupe patch is active as early as possible
try:
    from ..patches import ban_dedupe  # noqa: F401
except Exception:
    pass

log = logging.getLogger(__name__)

DEFAULT_SKIP = {"commands_probe"}  # keep parity
# Allow disabling cogs via env (CSV)
DISABLED_COGS = set((os.getenv("DISABLED_COGS") or "image_poster").split(","))

def _iter_cogs_package(package_name: str):
    """Yield fully-qualified module names for a cogs package."""
    try:
        pkg = importlib.import_module(package_name)
    except Exception:
        return []
    try:
        for mod in pkgutil.iter_modules(pkg.__path__, package_name + "."):
            yield mod.name
    except Exception:
        return []

def _iter_all_candidates():
    # Nixe-first; allow override base via env NIXE_COGS_BASE (CSV)
    bases = [x.strip() for x in (os.getenv("NIXE_COGS_BASE") or "nixe.cogs").split(",") if x.strip()]
    # Also probe legacy paths if user wants to co-host cogs
    bases += ["modules.discord_bot.cogs", "discord_bot.cogs"]
    seen = set()
    for base in bases:
        for name in _iter_cogs_package(base):
            if name not in seen:
                seen.add(name)
                yield name

async def load_all(bot):
    """Auto-discover & load all cogs; don't block startup on failures."""
    loaded = set()
    for name in _iter_all_candidates():
        base = name.split(".")[-1]
        if base in loaded or base in DEFAULT_SKIP or base in DISABLED_COGS:
            continue
        try:
            await bot.load_extension(name)
            loaded.add(base)
            log.info("[cogs_loader] loaded %s", name)
        except Exception:
            log.debug("[cogs_loader] skip %s", name, exc_info=True)

async def setup(bot):
    # For discord.py 2.x extension API
    await load_all(bot)