# -*- coding: utf-8 -*-
# Locked numeric IDs so smoketest can evaluate without imports
PHASH_DB_THREAD_ID = 1430048839556927589
# Optional pin to message in that thread (0 = disabled/auto)
PHASH_DB_MESSAGE_ID = 0
# Thread to read imagephishing inbox (learning)
PHASH_IMAGEPHISH_THREAD_ID = 1409949797313679492

# Safety policies
PHASH_DB_STRICT_EDIT = True           # must edit existing board message; never create new ones
PHASH_DB_MAX_ITEMS = 5000
PHASH_BOARD_EDIT_MIN_INTERVAL = 180

# Ban behavior (NIXE)
BAN_DRY_RUN = 0
BAN_DELETE_SECONDS = 86400
PHASH_HAMMING_MAX = 0
