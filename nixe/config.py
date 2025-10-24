# -*- coding: utf-8 -*-
THREAD_NIXE         = 1431192568221270108
THREAD_IMAGEPHISH   = 1409949797313679492
THREAD_IMAGEPHISING = THREAD_IMAGEPHISH
__all__ = ["THREAD_NIXE","THREAD_IMAGEPHISH","THREAD_IMAGEPHISING"]


import os
import logging
log=logging.getLogger(__name__)
def _env_int(key, default=None):
    v = os.getenv(key)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except Exception:
        try:
            return int(str(v).strip())
        except Exception:
            log.warning("Invalid int for %s=%r", key, v)
            return default

PHISH_LOG_CHAN_ID = _env_int('NIXE_PHISH_LOG_CHAN_ID')

PHASH_SOURCE_THREAD_ID = _env_int('NIXE_PHASH_SOURCE_THREAD_ID', _env_int('PHASH_IMAGEPHISH_THREAD_ID'))

PHASH_DB_THREAD_NAME = os.getenv('NIXE_PHASH_DB_THREAD_NAME', os.getenv('PHISH_DB_THREAD_NAME', 'phash-db'))

PHASH_DB_THREAD_ID = _env_int('NIXE_PHASH_DB_THREAD_ID', _env_int('PHASH_DB_THREAD_ID'))

LOG_PHISH_OBSERVED = os.getenv('NIXE_LOG_PHISH_OBSERVED', '0') == '1'

LOG_CHANNEL_ID = _env_int('LOG_CHANNEL_ID')
