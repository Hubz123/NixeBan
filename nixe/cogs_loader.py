# -*- coding: utf-8 -*-
from __future__ import annotations
import pkgutil, importlib, logging

LOGGER = logging.getLogger(__name__)

async def load_all(bot, package_root: str = "nixe.cogs"):
    """Minimal loader: imports all modules under nixe.cogs (excludes dunder & pycache).
    Skips modules ending with '.__pycache__' and avoids double-load exceptions.
    """
    try:
        pkg = importlib.import_module(package_root)
    except Exception as e:
        LOGGER.warning("cogs_loader.load_all: cannot import %s: %s", package_root, e)
        return
    for mod in pkgutil.iter_modules(pkg.__path__, package_root + "."):
        name = mod.name
        if name.split(".")[-1].startswith("_"):
            continue
        try:
            await bot.load_extension(name)
        except Exception as e:
            # keep going; Render free may race sometimes
            LOGGER.debug("skip %s: %s", name, e)
