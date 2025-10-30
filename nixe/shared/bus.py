# lightweight cross-cog message handling flag
import time
from typing import Dict

_DELETED: Dict[int, float] = {}

def mark_deleted(msg_id: int, ttl: int = 15) -> None:
    try:
        _DELETED[msg_id] = time.time() + ttl
    except Exception:
        pass

def is_deleted(msg_id: int) -> bool:
    try:
        exp = _DELETED.get(int(msg_id), 0.0)
        return exp > time.time()
    except Exception:
        return False
