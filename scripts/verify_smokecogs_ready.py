
#!/usr/bin/env python3
import importlib, sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
for m in ["nixe.helpers.phash_board","nixe.config_phash","nixe.cogs_loader"]:
    try:
        importlib.import_module(m)
        print("[OK] import", m)
    except Exception as e:
        print("[FAIL] import", m, "->", repr(e))
