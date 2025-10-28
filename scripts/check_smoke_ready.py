
#!/usr/bin/env python3
import sys, os, importlib
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
mods = ['nixe.helpers.phash_board','nixe.config_phash','nixe.cogs_loader']
ok=True
for m in mods:
    try:
        importlib.import_module(m); print('[OK] import', m)
    except Exception as e:
        print('[FAIL] import', m, '->', repr(e)); ok=False
sys.exit(0 if ok else 1)
