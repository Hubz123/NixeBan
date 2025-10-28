
#!/usr/bin/env python3
import os, sys, runpy
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
target = os.path.join(ROOT, "scripts", "smoke_cogs.py")
if not os.path.exists(target):
    raise SystemExit("smoke_cogs.py not found under scripts/")
ns = {"__name__":"__main__","__file__":target}
runpy.run_path(target, run_name="__main__")
