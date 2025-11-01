# nixe/helpers/lpa_heuristics.py
import os, re
from typing import Tuple

DEFAULT_KEYWORDS = [
    "gacha", "pull", "wish", "wishing", "roll", "reroll", "banner",
    "rate up", "pity", "hard pity", "soft pity", "10x", "x10", "multi-pull",
    "ssr", "ur", "sr", "legendary", "rare",
    "ガチャ", "10連", "十連", "抽卡", "十连", "扭蛋"
]

NEGATIVE_HINTS = [
    "story", "chapter", "prologue", "epilogue", "credits", "dialogue",
    "only one", "mommy.", "mommy", "talk", "conversation",
]

def kw_regex(words):
    escaped = [re.escape(w) for w in words]
    return re.compile(r"(?i)(?:%s)" % "|".join(escaped))

KW_RX = kw_regex(DEFAULT_KEYWORDS)
NEG_RX = kw_regex(NEGATIVE_HINTS)

def score_text_basic(text: str) -> Tuple[float, int, int]:
    if not text:
        return 0.0, 0, 0
    kw_hits = len(KW_RX.findall(text))
    neg_hits = len(NEG_RX.findall(text))
    score = min(1.0, kw_hits * 0.25)
    if neg_hits > 0:
        score *= 0.4
    return score, kw_hits, neg_hits
