#!/usr/bin/env python3
import pathlib, re, sys
t = pathlib.Path("main.py").read_text(encoding="utf-8", errors="ignore")
ok = "await bot.process_commands(message)" in t
print("[CHECK process_commands]", "OK" if ok else "MISSING")
sys.exit(0 if ok else 2)
