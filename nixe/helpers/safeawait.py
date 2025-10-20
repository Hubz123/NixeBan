from __future__ import annotations
import asyncio
async def maybe_awaitable(x):
    if asyncio.iscoroutine(x):
        return await x
    return x
