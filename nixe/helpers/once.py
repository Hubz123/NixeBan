from __future__ import annotations
import time
from typing import Dict, Tuple

# Simple in-memory TTL cache for dedup (process-local)
_store: Dict[str, float] = {}

def once_sync(key: str, ttl: int = 10) -> bool:
    """Return True if key not seen within ttl; then record it.
    Used for dedup actions (e.g., ban)."""
    now = time.time()
    exp = _store.get(key, 0)
    if exp and exp > now:
        return False
    _store[key] = now + max(1, ttl)
    return True