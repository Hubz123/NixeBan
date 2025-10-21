# Simple in-memory flag set to mark messages that must skip pHash
# Safe to import across cogs.
from collections import deque

_MAX = 5000
_skip_phash_ids = set()
_queue = deque()

def mark_skip_phash(msg_id: int):
    if msg_id in _skip_phash_ids:
        return
    _skip_phash_ids.add(msg_id)
    _queue.append(msg_id)
    if len(_queue) > _MAX:
        old = _queue.popleft()
        _skip_phash_ids.discard(old)

def should_skip_phash(msg_id: int) -> bool:
    return msg_id in _skip_phash_ids
