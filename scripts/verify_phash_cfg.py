#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Robust verifier for nixe.config_phash.
- Ensures the project root is on sys.path even when executed from scripts/.
- Exits nonzero when fields are missing/invalid.
"""
import sys, importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    mod = importlib.import_module("nixe.config_phash")
except Exception as e:
    print("[FAIL] Tidak bisa import nixe.config_phash:", repr(e))
    print("Hint: jalankan dari root repo atau pastikan PYTHONPATH berisi path root.")
    sys.exit(2)

need = ["PHASH_DB_THREAD_ID","PHASH_DB_MESSAGE_ID","PHASH_IMAGEPHISH_THREAD_ID","PHASH_DB_STRICT_EDIT"]
missing = [k for k in need if not hasattr(mod, k)]
if missing:
    print("[FAIL] Field hilang:", missing)
    sys.exit(3)

vals = {k:getattr(mod, k) for k in need}
if not vals["PHASH_DB_THREAD_ID"] or not vals["PHASH_IMAGEPHISH_THREAD_ID"]:
    print("[FAIL] Salah satu THREAD_ID bernilai 0:", vals)
    sys.exit(4)

print("[OK] pHash config terdeteksi:", vals)
sys.exit(0)
