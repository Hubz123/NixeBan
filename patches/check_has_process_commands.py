#!/usr/bin/env python3
import re, sys, pathlib
p = pathlib.Path("main.py")
t = p.read_text(encoding="utf-8", errors="ignore")
ok = "await bot.process_commands(message)" in t
print("[CHECK]", "FOUND process_commands ✅" if ok else "MISSING process_commands ❌")
sys.exit(0 if ok else 2)
