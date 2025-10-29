# -*- coding: utf-8 -*-
from __future__ import annotations
import os, threading

_lock = threading.RLock()
_P_HASH_THREAD_ID:int = int(os.getenv("PHASH_DB_THREAD_ID", "0") or 0)
_P_HASH_MSG_ID:int    = int(os.getenv("PHASH_DB_MESSAGE_ID", "0") or 0)

def get_phash_ids():
    with _lock:
        return _P_HASH_THREAD_ID, _P_HASH_MSG_ID

def set_phash_ids(thread_id: int | None = None, msg_id: int | None = None):
    global _P_HASH_THREAD_ID, _P_HASH_MSG_ID
    with _lock:
        if thread_id:
            _P_HASH_THREAD_ID = int(thread_id)
            os.environ["PHASH_DB_THREAD_ID"] = str(_P_HASH_THREAD_ID)
            os.environ["NIXE_PHASH_DB_THREAD_ID"] = str(_P_HASH_THREAD_ID)
        if msg_id:
            _P_HASH_MSG_ID = int(msg_id)
            os.environ["PHASH_DB_MESSAGE_ID"] = str(_P_HASH_MSG_ID)
