# scripts/smoke_lpa_provider_first.py
import os, importlib

os.environ.setdefault("LPA_EXECUTION_MODE","provider_first")
os.environ.setdefault("LPA_DEFER_IF_PROVIDER_DOWN","1")

try:
    BR = importlib.import_module("nixe.helpers.lpa_provider_bridge")
    score, reason = BR.classify("Only One\nMommy.", "groq,gemini")
    print("[SMOKE] provider classify ->", score, reason)
    print("== SUMMARY == OK (bridge importable; provider may be unavailable locally which is fine)")
except Exception as e:
    print("== SUMMARY == FAIL", repr(e))
    raise
