
Ported hashing logic into Nixe (neutral, no brand names). Files:
- nixe/helpers/img_hashing.py
- nixe/helpers/hash_utils.py
- nixe/cogs/a12_phash_inbox_port.py
- nixe/cogs/a13_phash_autoreseed_port.py

ENV toggles (defaults):
NIXE_ENABLE_HASH_PORT=1
NIXE_PHASH_SOURCE_THREAD_NAME=imagephising
PHASH_DB_MARKER=NIXE_PHASH_DB_V1
PHASH_MAX_FRAMES=6
PHASH_AUGMENT_REGISTER=1
PHASH_AUGMENT_PER_FRAME=5
TILE_GRID=3
PHISH_AUTO_RESEED_LIMIT=2000
PHISH_LOG_TTL=0
PHISH_NOTIFY_THREAD=0
