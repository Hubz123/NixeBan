# -*- coding: utf-8 -*-
"""
Minimal stub for nixe.ml.phash_reconcile to avoid hourly import errors.
Provides async collect_phash_from_log(channel, limit_msgs=..., ...)->list
You can replace this with a real implementation later.
"""
from __future__ import annotations
from typing import Any, List

async def collect_phash_from_log(channel: Any, limit_msgs: int = 400, *args, **kwargs) -> List[Any]:
    # No-op: return empty list to indicate nothing collected.
    return []
