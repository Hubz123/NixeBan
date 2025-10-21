from __future__ import annotations
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
try:
    from nixe.config import self_learning_cfg as s
    print('PHASH_LOG_SCAN_LIMIT=', s.PHASH_LOG_SCAN_LIMIT)
    print('SELF_LEARNING_MAX_ITEMS=', s.SELF_LEARNING_MAX_ITEMS)
    print('BAN_BRAND_NAME=', s.BAN_BRAND_NAME)
    print('BAN_DRY_RUN=', s.BAN_DRY_RUN)
    print('NIXE_HEALTHZ_PATH=', s.NIXE_HEALTHZ_PATH)
    print('NIXE_HEALTHZ_SILENCE=', s.NIXE_HEALTHZ_SILENCE)
except Exception as e:
    print('config helper failed:', e)
