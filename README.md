# Nixe: Lucky Pull Guard (Random-Only Persona)
- Persona `yandere` sekarang **random-only** (soft/agro/sharp), tanpa weight/score.
- Guard **sangat konservatif**: tidak akan menghapus apa pun kecuali keyakinan >= `min_confidence_delete`.
- Jika confidence moderat, konten **hanya dipindah** ke channel redirect (jika diset), **tanpa delete**.
- Jika confidence rendah, **dibiarkan** (tidak dihapus, tidak dipindah).

## Konfigurasi
Edit `nixe/config/gacha_guard.json`:
- `guard_channels`: daftar channel yang *dilarang* untuk gambar lucky pull.
- `redirect_channel`: channel tujuan untuk memindahkan konten.
- `min_confidence_delete` (default 0.85), `min_confidence_redirect` (0.60).
- Tanpa ENV tambahan; semua lewat JSON.

## Integrasi Gemini (opsional)
Modul `nixe/helpers/lucky_classifier.py` menerima `gemini_label` & `gemini_conf` (**0..1**). Panggil sendiri modelmu di cogs lain,
lalu saat memanggil `classify_image_meta(...)` operkan `gemini_label/conf` untuk meningkatkan kepastian.
Dengan dua sinyal (filename + gemini), confidence akan naik sedikit, tetap konservatif.

## Smoke
```bash
python scripts/smoke_gacha_guard_random_only.py
```
