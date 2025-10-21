"""Nixe config loader (safe defaults for smoke + runtime)"""
from __future__ import annotations
import os
from typing import Any, Dict
DEFAULTS: Dict[str, Any] = {}
OVERRIDES: Dict[str, Any] = {}
class _CfgNS:
    def __init__(self, d: Dict[str, Any]):
        self.__dict__.update(d)
        self.image = {
            "phash_distance_strict": int(os.getenv("PHASH_DISTANCE_STRICT", "6")),
            "phash_distance_lenient": int(os.getenv("PHASH_DISTANCE_LENIENT", "10")),
            "warmup_seconds": int(os.getenv("PHASH_WARMUP_SECONDS", "0")),
            "ban_cooldown_seconds": int(os.getenv("BAN_COOLDOWN_SECONDS", "10")),
            "ban_ceiling_per_10min": int(os.getenv("BAN_CEILING_PER_10MIN", "5")),
        }
def load() -> _CfgNS:
    cfg: Dict[str, Any] = dict(DEFAULTS); cfg.update(OVERRIDES); return _CfgNS(cfg)
