# -*- coding: utf-8 -*-
"""
Project cog loader for NIXE — TB de-dup + quiet idle.

- Dedup: if a TB provider is already present, skip loading another TB provider.
  * Default provider = 'external'. Configure via NIXE_TB_PROVIDER env:
      NIXE_TB_PROVIDER=external   -> keep a01_external_tb, skip a01_manual_tb
      NIXE_TB_PROVIDER=manual  -> keep a01_manual_tb, skip a01_external_tb
      NIXE_TB_PROVIDER=both    -> load keduanya (tidak direkomendasikan; akan dobel)
- Idle log filter for 'phash_hourly_scheduler' (same as previous patch):
      PHASH_HOURLY_VERBOSE=1          -> disable filter
      PHASH_HOURLY_IDLE_LOG_EVERY=900 -> interval (detik), default 1800

"""
from __future__ import annotations
import asyncio
import logging
from nixe.cogs.cogs_loader_patch import apply_module_filter
import os
import time
from pkgutil import iter_modules

log = logging.getLogger("nixe.cogs_loader")
LOADED_COUNT = 0

def _apply_scheduler_idle_filter():
    verbose = str(os.getenv("PHASH_HOURLY_VERBOSE", "0")).lower()
    if verbose in {"1","true","yes","on","debug"}:
        log.info("phash_hourly_scheduler verbose mode enabled (no idle filter).")
        return
    idle_every = int(os.getenv("PHASH_HOURLY_IDLE_LOG_EVERY", "1800"))
    target = logging.getLogger("nixe.cogs.phash_hourly_scheduler")
    class _IdleFilter(logging.Filter):
        def __init__(self):
            super().__init__()
            self._last = 0.0
            self._needle = "collected phash (fallback): ~0 entries"
        def filter(self, record: logging.LogRecord) -> bool:
            try:
                msg = record.getMessage()
            except Exception:
                return True
            if self._needle in msg:
                now = time.monotonic()
                if now - self._last < idle_every:
                    return False
                self._last = now
            return True
    target.addFilter(_IdleFilter())
    log.info("Applied idle filter to phash_hourly_scheduler (every=%ss).", idle_every)

_apply_scheduler_idle_filter()

# --- Discovery & ordering
SKIP = {"__pycache__"}
PRIORITY_FIRST = ["ready_shim", "phash_rescanner"]
PRIORITY_LAST  = ["phash_hourly_scheduler"]

def _discover():
    import nixe.cogs as pkg
    base = pkg.__name__ + "."
    names = [m.name for m in iter_modules(pkg.__path__) if not m.ispkg and m.name not in SKIP and not m.name.startswith("_")]
    def key(n):
        if n in PRIORITY_FIRST: return (0, n)
        if n in PRIORITY_LAST:  return (2, n)
        return (1, n)
    names.sort(key=key)
    return [base + n for n in names]

def _should_skip_tb(modname: str, bot) -> bool:
    provider_pref = (os.getenv("NIXE_TB_PROVIDER") or "manual").lower()
    is_external  = modname.endswith(".a01_external_tb")
    is_manual = modname.endswith(".a01_manual_tb")

    if provider_pref == "both":
        return False
    if provider_pref == "external" and is_manual:
        return True
    if provider_pref == "manual" and is_external:
        return True

    # Auto-dedupe: if 'tb' command already registered, skip the second provider
    try:
        tb_exists = "tb" in getattr(bot, "all_commands", {})
    except Exception:
        tb_exists = False
    if tb_exists and (is_external or is_manual):
        return True
    return False

async def autoload_all(bot) -> int:
    global LOADED_COUNT
    LOADED_COUNT = 0
    for modname in _discover():
        if _should_skip_tb(modname, bot):
            log.info("⏭️  Skip TB provider due to preference/dedupe: %s", modname)
            continue
        try:
            await bot.load_extension(modname)
            LOADED_COUNT += 1
            log.info("✅ Loaded cog: %s", modname)
        except Exception as e:
            log.error("Failed to load %s: %r", modname, e)
    log.info("✅ Cogs loaded (project loader): %d", LOADED_COUNT)
    return LOADED_COUNT

def load_all(bot):
    return asyncio.get_event_loop().run_until_complete(autoload_all(bot))
