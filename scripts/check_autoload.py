#!/usr/bin/env python3
import pathlib, re, sys
t = pathlib.Path("main.py").read_text(encoding="utf-8", errors="ignore")
ok1 = "_autoload_all_cogs" in t
ok2 = "_autoload_all_cogs(bot)" in t
print("[CHECK autoload]", ("OK func" if ok1 else "MISS func"), "|", ("OK call" if ok2 else "MISS call"))
sys.exit(0 if (ok1 and ok2) else 2)
