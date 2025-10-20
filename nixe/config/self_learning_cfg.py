from __future__ import annotations
import os
def _to_int(*keys, default=0):
    for k in keys:
        v = os.getenv(k)
        if v is None: continue
        try: return int(v)
        except Exception: pass
    return default
def _to_str(*keys, default=''):
    for k in keys:
        v = os.getenv(k)
        if v: return v
    return default
BAN_LOG_CHANNEL_ID = _to_int('NIXE_BAN_LOG_CHANNEL_ID','BAN_LOG_CHANNEL_ID','LOG_CHANNEL_ID', default=0)
LOG_CHANNEL_ID = BAN_LOG_CHANNEL_ID
PHASH_INBOX_THREAD = _to_str('NIXE_PHASH_INBOX_THREAD','PHASH_INBOX_THREAD',
    default='imagephising,imagelogphising,image-phising,image_phising,image-phishing,image_phishing')
PHASH_DB_MARKER = _to_str('PHASH_DB_MARKER', default='SATPAMBOT_PHASH_DB_V1')
PHASH_WATCH_FIRST_DELAY = _to_int('PHASH_WATCH_FIRST_DELAY', default=60)
PHASH_WATCH_INTERVAL = _to_int('PHASH_WATCH_INTERVAL', default=600)
PHASH_HAMMING_MAX = _to_int('PHASH_HAMMING_MAX', default=0)
PHASH_AUTOBAN_ENABLED = bool(int(os.getenv('PHASH_AUTOBAN_ENABLED','0')))
LINK_DB_MARKER = _to_str('LINK_DB_MARKER', default='SATPAMBOT_LINK_BLACKLIST_V1')
BAN_DELETE_SECONDS = _to_int('BAN_DELETE_SECONDS', default=0)
BAN_DRY_RUN = bool(int(os.getenv('BAN_DRY_RUN','1')))
BAN_BRAND_NAME = _to_str('BAN_BRAND_NAME', default='SatpamBot')
NIXE_HEALTHZ_PATH = _to_str('NIXE_HEALTHZ_PATH', default='/healthz')
NIXE_HEALTHZ_SILENCE = bool(int(os.getenv('NIXE_HEALTHZ_SILENCE','1')))
