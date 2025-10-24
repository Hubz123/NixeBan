#!/usr/bin/env python3
import importlib, sys
ok = True

for modname in ("nixe.config", "nixe.config_ids", "nixe.config.self_learning_cfg"):
    try:
        m = importlib.import_module(modname)
        tn = getattr(m, "THREAD_NIXE", getattr(m, "THREAD_NIXE_DB", 0))
        ti = getattr(m, "THREAD_IMAGEPHISH", getattr(m, "THREAD_IMAGEPHISING", 0))
        print(f"[{modname}] THREAD_NIXE={tn}  THREAD_IMAGEPHISH={ti}")
        if int(tn) == 0 or int(ti) == 0:
            ok = False
    except Exception as e:
        print(f"[{modname}] import error: {e!r}")
        ok = False

sys.exit(0 if ok else 2)
