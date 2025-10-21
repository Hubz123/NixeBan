from __future__ import annotations
import time, threading

_lock = threading.RLock()
_seen: dict[str, float] = {}

def once_sync(key: str, ttl: int = 10) -> bool:
    """Return True if first time within TTL; else False."""
    now = time.time()
    with _lock:
        exp = _seen.get(key)
        if exp and exp > now:
            return False
        _seen[key] = now + max(1, ttl)
        # periodic cleanup
        if len(_seen) > 1000:
            _gc = [k for k,v in _seen.items() if v < now]
            for k in _gc:
                _seen.pop(k, None)
        return True
