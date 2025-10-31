import sys, os
sys.path.insert(0, '.')
from nixe.helpers.persona_loader import list_groups, pick_line
g = set(list_groups('yandere'))
ok = bool(g)
print('[DEBUG] groups:', g)
s = pick_line('yandere', user='kamu', channel='#test', reason='lucky pull')
print('[DEBUG] sample:', s)
if not g or not s:
    print('[FAIL] persona source not usable')
    sys.exit(1)
print('[PASS] yandere.json is active and usable')
