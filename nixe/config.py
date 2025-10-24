# -*- coding: utf-8 -*-
THREAD_NIXE         = 1430048839556927589
THREAD_IMAGEPHISH   = 1409949797313679492
THREAD_IMAGEPHISING = THREAD_IMAGEPHISH
try:
    from ..config_ids import BAN_BRAND_NAME as BAN_BRAND_NAME
except Exception:
    try:
        from nixe.config_ids import BAN_BRAND_NAME as BAN_BRAND_NAME
    except Exception:
        BAN_BRAND_NAME = "SatpamBot"
__all__ = ["THREAD_NIXE","THREAD_IMAGEPHISH","THREAD_IMAGEPHISING","BAN_BRAND_NAME"]
