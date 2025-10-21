from __future__ import annotations
import os

# ---- Compatibility constants expected by legacy Leina/Nixe cogs & smoke ----
# Prefer ENV overrides to avoid editing code in production.

# Scanning/log limits (raised maximums by default, still safe):
PHASH_LOG_SCAN_LIMIT: int = int(os.getenv('PHASH_LOG_SCAN_LIMIT', '5000'))
SELF_LEARNING_ENABLE: bool = os.getenv('SELF_LEARNING_ENABLE', '0').lower() in {'1','true','yes','on'}
SELF_LEARNING_MAX_ITEMS: int = int(os.getenv('SELF_LEARNING_MAX_ITEMS', '20000'))

# Branding / behavior flags:
BAN_BRAND_NAME: str = os.getenv('BAN_BRAND_NAME', os.getenv('BRAND_NAME', 'NIXE'))
BAN_DRY_RUN: bool = os.getenv('BAN_DRY_RUN', '0').lower() in {'1','true','yes','on'}

# Healthz controls:
NIXE_HEALTHZ_PATH: str = os.getenv('NIXE_HEALTHZ_PATH', '/healthz')
NIXE_HEALTHZ_SILENCE: bool = os.getenv('NIXE_HEALTHZ_SILENCE', '1').lower() in {'1','true','yes','on'}
NIXE_HEALTHZ_TOKEN: str = os.getenv('NIXE_HEALTHZ_TOKEN', '')

# Logging / channels (bridge)
try:
    from .__init__ import BAN_LOG_CHANNEL_ID  # type: ignore
except Exception:
    BAN_LOG_CHANNEL_ID: int = int(os.getenv('BAN_LOG_CHANNEL_ID', '0'))

# Also expose plain LOG_CHANNEL_ID for older cogs
LOG_CHANNEL_ID: int = int(os.getenv('LOG_CHANNEL_ID', str(BAN_LOG_CHANNEL_ID)))

try:
    from .__init__ import URL_BAN_PATTERNS  # type: ignore
except Exception:
    URL_BAN_PATTERNS = []

# ---- Link phishing guard knobs ----
LINK_DB_MARKER: str = os.getenv('LINK_DB_MARKER', 'NIXE_LINK_DB')
SAFE_ALLOWLIST = [s.strip().lower() for s in os.getenv('SAFE_ALLOWLIST', '').split(',') if s.strip()]
EXACT_MATCH_ONLY: bool = os.getenv('EXACT_MATCH_ONLY', '0').lower() in {'1','true','yes','on'}
BAN_DELETE_SECONDS: int = int(os.getenv('BAN_DELETE_SECONDS', '10'))

# ---- pHash guard knobs ----
PHASH_INBOX_THREAD: str = os.getenv('PHASH_INBOX_THREAD', 'inbox,phisinbox')
PHASH_AUTOBAN_ENABLED: bool = os.getenv('PHASH_AUTOBAN_ENABLED', '1').lower() in {'1','true','yes','on'}
PHASH_HAMMING_MAX: int = int(os.getenv('PHASH_HAMMING_MAX', '10'))
PHASH_DB_MARKER: str = os.getenv('PHASH_DB_MARKER', 'NIXE_PHASH_DB')
PHASH_WATCH_FIRST_DELAY: int = int(os.getenv('PHASH_WATCH_FIRST_DELAY', '5'))
PHASH_WATCH_INTERVAL: int = int(os.getenv('PHASH_WATCH_INTERVAL', '180'))  # 3 minutes check
PHASH_FIRST_DELAY_SECONDS: int = int(os.getenv('PHASH_FIRST_DELAY_SECONDS', '5'))
PHASH_INTERVAL_SECONDS: int = int(os.getenv('PHASH_INTERVAL_SECONDS', '3600'))

__all__ = [
    'PHASH_LOG_SCAN_LIMIT', 'SELF_LEARNING_ENABLE', 'SELF_LEARNING_MAX_ITEMS',
    'BAN_BRAND_NAME', 'BAN_DRY_RUN',
    'NIXE_HEALTHZ_PATH', 'NIXE_HEALTHZ_SILENCE', 'NIXE_HEALTHZ_TOKEN',
    'BAN_LOG_CHANNEL_ID', 'LOG_CHANNEL_ID', 'URL_BAN_PATTERNS',
    'LINK_DB_MARKER', 'SAFE_ALLOWLIST', 'EXACT_MATCH_ONLY', 'BAN_DELETE_SECONDS',
    'PHASH_INBOX_THREAD', 'PHASH_AUTOBAN_ENABLED', 'PHASH_HAMMING_MAX',
    'PHASH_DB_MARKER', 'PHASH_WATCH_FIRST_DELAY', 'PHASH_WATCH_INTERVAL',
    'PHASH_FIRST_DELAY_SECONDS', 'PHASH_INTERVAL_SECONDS',
]
