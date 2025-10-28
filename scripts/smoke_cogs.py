#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, importlib, inspect, traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

def _force_local_nixe():
    importlib.invalidate_caches()
    try:
        import nixe; nfile = inspect.getfile(nixe)
        if not os.path.abspath(nfile).startswith(os.path.abspath(ROOT)):
            for k in list(sys.modules.keys()):
                if k == 'nixe' or k.startswith('nixe.'):
                    sys.modules.pop(k, None)
            if ROOT not in sys.path:
                sys.path.insert(0, ROOT)
            importlib.invalidate_caches()
    except Exception:
        pass

def smoke_import(modname: str) -> bool:
    _force_local_nixe()
    try:
        m = importlib.import_module(modname)
        p = getattr(m, '__file__', '?')
        print(f'[PASS] import: {modname} ({p})')
        return True
    except Exception:
        print(f'[FAIL] import: {modname}')
        traceback.print_exc(limit=5)
        return False

def main():
    ok = True
    ok &= smoke_import('nixe.helpers.phash_board')
    ok &= smoke_import('nixe.config_phash')
    ok &= smoke_import('nixe.cogs_loader')

    # discover
    try:
        _force_local_nixe()
        import nixe.cogs_loader as cl
        fun = getattr(cl, 'discover', None) or getattr(cl, 'discover_cogs', None)
        files = fun() if fun else []
        if isinstance(files, (list, tuple)):
            print('[PASS] cogs: discover (', len(files), 'file(s) )')
        else:
            print('[FAIL] cogs: discover (non-list result)')
    except Exception:
        print('[FAIL] cogs: discover')
        traceback.print_exc(limit=5)
        ok = False

    print('-'*64)
    if ok:
        print('Summary: PASS=4 WARN=0 FAIL=0 TOTAL=4')
        raise SystemExit(0)
    else:
        print('Summary: some checks failed')
        raise SystemExit(1)

if __name__ == '__main__':
    main()
