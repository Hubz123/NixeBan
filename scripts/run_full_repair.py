#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(cmd):
    print('+', ' '.join(cmd))
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        print('! command failed:', cmd)
        sys.exit(r.returncode)

def main():
    run([sys.executable, 'scripts/repair_quotes_all.py'])
    print('All repair steps completed.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
