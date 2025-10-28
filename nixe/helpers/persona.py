from __future__ import annotations
from .persona_loader import pick_line

def yandere(**fmt) -> str:
    """Random-only yandere line (soft/agro/sharp)."""
    return pick_line("yandere", **fmt)
