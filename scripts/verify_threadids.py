#!/usr/bin/env python3
import importlib
mods = ["nixe.config", "nixe.config_ids", "nixe.config.self_learning_cfg"]
for m in mods:
    mod = importlib.import_module(m)
    tn = getattr(mod, "THREAD_NIXE", getattr(mod, "THREAD_NIXE_DB", 0))
    ti = getattr(mod, "THREAD_IMAGEPHISH", getattr(mod, "THREAD_IMAGEPHISING", 0))
    print(f"[{m}] THREAD_NIXE={tn}  THREAD_IMAGEPHISH={ti}")
