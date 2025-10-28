# Personas (v2)
- Tambah tone `possessive` (alias: `killer`, `yandere_killer`, `poss`), gaya yandere posesif ala anime namun aman untuk moderasi (tanpa ajakan kekerasan).
- Mode pemilihan:
  - `weighted` (default): gunakan `select.weights`
  - `random`: seluruh tone peluang sama
  - `by_score`: peta skor 0..100 ke tone via `select.score_buckets`

## Pakai di cogs
```py
from nixe.helpers.persona import yandere

# 1) random mode setara
msg = yandere(mode="random", user=member.mention, channel="#general", reason="deteksi lucky pull")

# 2) explicit tone
msg = yandere(tone="possessive", user=member.mention, channel="#general", reason="deteksi lucky pull")

# 3) by_score (misal dari output Gemini 0..100)
msg = yandere(mode="by_score", score=87, user=member.mention, channel="#general", reason="deteksi lucky pull")
```

## Schema tambahan
- `select.aliases`: peta alias → tone
- `select.score_buckets`: peta tone → [low, high]
