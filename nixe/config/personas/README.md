# Personas
Letakkan file template persona di sini (JSON per persona). Contoh: `yandere.json`.

## Skema ringkas
- version: integer
- persona: nama persona
- locale: kode bahasa (opsional)
- placeholders: daftar placeholder yang bisa dipakai di template
- select.strategy: cara pemilihan (random/random_weighted)
- select.weights: bobot per grup (jika random_weighted)
- groups: dict {tone: [template1, template2, ...]}

Gunakan placeholder Python `.format`, misal: `{user}`, `{channel}`, `{reason}`.
