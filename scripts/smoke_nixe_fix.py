# -*- coding: utf-8 -*-
import sys, traceback
from pathlib import Path
from scripts._bootstrap_import import whereis  # adds repo root to sys.path

def _try(label, target):
    try:
        __import__(target)
        print(f"[OK] import {target}: {whereis(target)}")
        return True
    except Exception as e:
        print(f"[FAIL] import {target}: {e.__class__.__name__}: {e}")
        if hasattr(e, "__cause__") and e.__cause__:
            print(f"  cause: {e.__cause__}")
        return False

ROOT = Path(__file__).resolve().parents[1]
print(f"[INFO] cwd={Path.cwd()}")
print(f"[INFO] repo_root={ROOT}")
# Basic imports
ok_pkg = _try("pkg", "nixe")
ok_env = _try("env", "nixe.config.env")
ok_bridge = _try("bridge", "nixe.helpers.gemini_bridge")
ok_guard = _try("guard", "nixe.cogs.lucky_pull_guard")
ok_loader = _try("loader", "nixe.cogs.a15_lucky_pull_guard_loader")
ok_auto = _try("auto", "nixe.cogs.lucky_pull_auto")

print("--------------------------------------------------------")
fails = sum([not ok_pkg, not ok_env, not ok_bridge, not ok_guard, not ok_loader, not ok_auto])
print(f"Summary: {'OK' if fails==0 else 'FAIL'} (failures={fails})")
sys.exit(1 if fails else 0)
