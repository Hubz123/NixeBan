# -*- coding: utf-8 -*-
from __future__ import annotations
import pkgutil, importlib, logging, asyncio

LOGGER = logging.getLogger(__name__)

async def _load_all_impl(bot, package_root: str = "nixe.cogs") -> int:
    try:
        pkg = importlib.import_module(package_root)
    except Exception as e:
        LOGGER.warning("cogs_loader: cannot import %s: %s", package_root, e)
        return 0
    loaded = 0
    for mod in pkgutil.iter_modules(pkg.__path__, package_root + "."):
        name = mod.name
        leaf = name.rsplit(".", 1)[-1]
        if leaf.startswith("_"):
            continue
        try:
            await bot.load_extension(name)
            loaded += 1
            LOGGER.info("✅ Loaded cog: %s", name)
        except Exception as e:
            LOGGER.debug("skip %s: %s", name, e)
    LOGGER.info("cogs_loader: loaded %d cogs total", loaded)
    return loaded

def load_all(bot, package_root: str = "nixe.cogs"):
    """Safe entrypoint: works with or without 'await'."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        return asyncio.create_task(_load_all_impl(bot, package_root))
    tmp = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(tmp)
        return tmp.run_until_complete(_load_all_impl(bot, package_root))
    finally:
        try: tmp.close()
        except Exception: pass
