from __future__ import annotations
import pkgutil, logging
from discord.ext import commands

log = logging.getLogger(__name__)

CORE = [
    "nixe.cogs.a00_fix_task_bootstrap_overlay",
    "nixe.cogs.a00_graceful_shutdown",
    "nixe.cogs.banlog_redirect_shim",
    "nixe.cogs.cogs_loader",
    "nixe.cogs.gacha_luck_guard",
    "nixe.cogs.link_phish_guard",
    "nixe.cogs.image_phish_guard",
    "nixe.cogs.ban_commands",
    "nixe.cogs.phash_inbox_watcher",
    "nixe.cogs.phash_auto_ban",
    "nixe.cogs.phash_runtime_log_tamer",
    "nixe.cogs.phash_compactify",
    "nixe.cogs.ready_shim",
]

FALLBACK = {
    "nixe.cogs.link_phish_guard": "nixe.cogs._fix.link_phish_guard_fix",
    "nixe.cogs.image_phish_guard": "nixe.cogs._fix.image_phish_guard_fix",
    "nixe.cogs.ban_commands": "nixe.cogs._fix.ban_commands_fix",
    "nixe.cogs.phash_inbox_watcher": "nixe.cogs._fix.phash_inbox_watcher_fix",
}

async def _try_load(bot: commands.Bot, name: str):
    try:
        await bot.load_extension(name)
        log.info("✅ Loaded cog: %s", name)
        return True
    except Exception as e:
        log.warning("[loader] failed: %s (%s)", name, e)
        fb = FALLBACK.get(name)
        if fb:
            try:
                await bot.load_extension(fb)
                log.info("✅ Loaded fallback cog: %s", fb)
                return True
            except Exception as ee:
                log.warning("[loader] fallback failed: %s (%s)", fb, ee)
        return False

async def load_cogs(bot: commands.Bot):
    loaded = set()
    for name in CORE:
        if name in loaded:
            continue
        ok = await _try_load(bot, name)
        if ok:
            loaded.add(name)

    try:
        import nixe.cogs as pkg
        for m in pkgutil.iter_modules(pkg.__path__):
            if m.name in {"cogs_loader", "loader_leina"}:
                continue
            mod = f"nixe.cogs.{m.name}"
            if mod in loaded or mod in FALLBACK.values():
                continue
            await _try_load(bot, mod)
    except Exception as e:
        log.debug("cogs autodiscovery failed: %s", e)
