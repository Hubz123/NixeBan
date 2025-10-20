from __future__ import annotations
# Proxy constants to module config (nixe.config.__init__)
# All settings come from module defaults; ENV is optional and not required.

from . import image as _image, link as _link, ban as _ban, healthz as _healthz

# BAN / LOG
BAN_LOG_CHANNEL_ID = _ban.get("BAN_LOG_CHANNEL_ID", 0) or _ban.get("LOG_CHANNEL_ID", 0)
LOG_CHANNEL_ID = BAN_LOG_CHANNEL_ID
BAN_DELETE_SECONDS = int(_ban.get("BAN_DELETE_SECONDS", 0) or 0)
BAN_DRY_RUN = bool(_ban.get("BAN_DRY_RUN", False))
BAN_BRAND_NAME = _ban.get("BAN_BRAND_NAME", "NIXE")

# PHASH / IMAGE inbox watcher
PHASH_INBOX_THREAD = _image.get("PHASH_INBOX_THREAD", "imagephising,imagelogphising,image-phising,image_phising,image-phishing,image_phishing")
PHASH_DB_MARKER = _image.get("PHASH_DB_MARKER", "NIXE_PHASH_DB_V1")
PHASH_WATCH_FIRST_DELAY = int(_image.get("PHASH_WATCH_FIRST_DELAY", 60) or 60)
PHASH_WATCH_INTERVAL = int(_image.get("PHASH_WATCH_INTERVAL", 600) or 600)
PHASH_HAMMING_MAX = int(_image.get("PHASH_HAMMING_MAX", 0) or 0)
PHASH_AUTOBAN_ENABLED = bool(_image.get("PHASH_AUTOBAN_ENABLED", False))

# LINK blacklist
LINK_DB_MARKER = _link.get("LINK_DB_MARKER", "NIXE_LINK_BLACKLIST_V1")

# Healthz
NIXE_HEALTHZ_PATH = _healthz.get("PATH", "/healthz")
NIXE_HEALTHZ_SILENCE = bool(_healthz.get("SILENCE", True))


# Link guard extras
SAFE_ALLOWLIST = set(_link.get("SAFE_ALLOWLIST", []))
EXACT_MATCH_ONLY = bool(_link.get("EXACT_MATCH_ONLY", True))


# Phash scheduler timings & limits
PHASH_FIRST_DELAY_SECONDS = int(_image.get("PHASH_WATCH_FIRST_DELAY", 60) or 60)
PHASH_INTERVAL_SECONDS = int(_image.get("PHASH_WATCH_INTERVAL", 600) or 600)
PHASH_LOG_SCAN_LIMIT = int(_image.get("PHASH_LOG_SCAN_LIMIT", 300) or 300)

