
from __future__ import annotations
import asyncio

_cogs_loaded = asyncio.Event()

def mark_cogs_loaded() -> None:
    try:
        _cogs_loaded.set()
    except Exception:
        pass

async def wait_cogs_loaded(timeout: float = 5.0) -> None:
    try:
        await asyncio.wait_for(_cogs_loaded.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        # proceed anyway to avoid blocking startup logs
        return
