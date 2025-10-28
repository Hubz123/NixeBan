from __future__ import annotations
from typing import Optional
from .persona_loader import pick_line

def yandere(tone: Optional[str] = None, **fmt) -> str:
    """Shortcut for Nixe's Yandere persona line selection."""
    return pick_line("yandere", tone=tone, **fmt)
