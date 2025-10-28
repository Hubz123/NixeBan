#!/usr/bin/env python3
import importlib, inspect, sys, os

# Ensure repo root (parent of /scripts) is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    mod = importlib.import_module("nixe.cogs.luckypull_guard")
except Exception as e:
    print("[FAIL] import nixe.cogs.luckypull_guard:", repr(e))
    print("Hint: run from repo root or ensure sys.path includes the repo root containing the 'nixe' package.")
    raise SystemExit(1)

setup = getattr(mod, "setup", None)
if not setup or not inspect.iscoroutinefunction(setup):
    print("[FAIL] setup(bot) missing or not async in nixe.cogs.luckypull_guard")
    raise SystemExit(1)

print("[OK] import nixe.cogs.luckypull_guard")
print("[OK] async setup(bot) present")
print("SMOKE: PASS")
