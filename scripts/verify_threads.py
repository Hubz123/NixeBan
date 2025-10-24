#!/usr/bin/env python3
import importlib, sys
mods = ["nixe.config", "nixe.config_ids", "nixe.config.self_learning_cfg"]
ok = True
for m in mods:
    try:
        mod = importlib.import_module(m)
        tn = getattr(mod, "THREAD_NIXE", getattr(mod, "THREAD_NIXE_DB", 0))
        ti = getattr(mod, "THREAD_IMAGEPHISH", getattr(mod, "THREAD_IMAGEPHISING", 0))
        print(f"[{m}] THREAD_NIXE={tn}  THREAD_IMAGEPHISH={ti}")
        if int(tn) == 0 or int(ti) == 0:
            ok = False
    except Exception as e:
        print(f"[{m}] import error: {e!r}")
        ok = False
sys.exit(0 if ok else 2)
