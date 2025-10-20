# nixe/config/link.py  (v9 submodule: expose constants)
from __future__ import annotations
from . import load as _load
DATA = _load("link")
globals().update(DATA)
__all__ = list(DATA.keys()) + ["DATA"]
