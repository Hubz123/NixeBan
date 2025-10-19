# nixe/config/self_learning_cfg.py
from __future__ import annotations
import os

def _int_env(*keys: str, default: int = 0) -> int:
    for k in keys:
        v = os.getenv(k)
        if v is None: 
            continue
        try:
            return int(v)
        except Exception:
            pass
    return default

# Sumber kebenaran baru untuk seluruh log BAN/TEST BAN
# Prioritas ENV:
# 1) NIXE_BAN_LOG_CHANNEL_ID
# 2) BAN_LOG_CHANNEL_ID (untuk kompat)
# 3) LOG_CHANNEL_ID (fallback umum)
BAN_LOG_CHANNEL_ID: int = _int_env("NIXE_BAN_LOG_CHANNEL_ID", "BAN_LOG_CHANNEL_ID", "LOG_CHANNEL_ID", default=0)

# Jika ingin dibedakan, siapkan ENV terpisah; default samakan
LOG_CHANNEL_ID: int = BAN_LOG_CHANNEL_ID
