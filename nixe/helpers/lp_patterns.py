
# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from typing import List, Pattern

DEFAULT_KEYWORDS = [
    r"\blucky\b", r"\bpull(s|ed)?\b", r"\broll(s|ed)?\b", r"\bwarp(s|ed)?\b",
    r"\bwish(es|ed)?\b", r"\bpity\b", r"\brate\s*up\b", r"\bbanner\b",
    r"\bgacha\b", r"\bcongrats\b", r"\bcharacter\s*event\b",
    r"\bstandard\s*banner\b", r"\blimited\s*(banner|event)\b",
    r"\bhonkai\b", r"\bstar\s*rail\b", r"\bwuthering\s*waves\b", r"\bhsr\b", r"\bhsr2\b"
]

def compile_from_env(raw: str | None) -> List[Pattern]:
    pats = []
    if raw:
        for token in [p.strip() for p in raw.split(",") if p.strip()]:
            try:
                pats.append(re.compile(token, re.IGNORECASE))
            except re.error:
                # ignore bad pattern
                pass
    # Always append defaults as a safety net
    for kw in DEFAULT_KEYWORDS:
        try:
            pats.append(re.compile(kw, re.IGNORECASE))
        except re.error:
            pass
    return pats

def match_any(text: str, pats: List[Pattern]) -> bool:
    if not text:
        return False
    for p in pats:
        if p.search(text):
            return True
    return False
