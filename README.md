# Nixe — Phish-Ban Discord Bot (STRICT, Render-ready)

Bot minimal khusus **ban phishing** (gambar & link) dengan fokus **meminimalkan false ban/false positive**.
Fitur utama:
- **Image phish guard**: MIME sniff (WEBP yang disamarkan), dHash→aHash fallback, DB pHash dari pin/thread.
- **Link guard**: normalisasi URL/domain (IDN → ASCII), blacklist + regex dari ENV/pin.
- **Safety**: tiered threshold (ban vs quarantine), cooldown & ban ceiling, warm-up, whitelist role, modlog.
- **Runtime mode**: `log` → `quarantine` → `ban` (bisa diubah via command tanpa redeploy).

## Quick start (local)
```bash
python -m pip install -r requirements.txt
cp .env.example .env
# isi BOT_TOKEN, PHISH_DB_THREAD_ID/CHANNEL_ID, MOD_LOG_CHANNEL_ID, dsb.
python main.py
```

## Render (Worker)
- Start: `python main.py`
- ENV: salin dari `.env.example` (jangan commit token)

## Permissions
Gunakan script `scripts/make_invite.py` untuk menghasilkan URL invite dengan bit permission yang tepat.



---

## CI & Deploy

- **CI**: GitHub Actions workflow `.github/workflows/nixe-ci.yml` akan menjalankan `smoke_cogs.py` dan `scripts/smoke_all.py` pada setiap push/PR.
- **Deploy (opsional)**: Tambahkan secret `RENDER_DEPLOY_HOOK_URL` di GitHub repo → workflow `.github/workflows/deploy.yml` akan memicu redeploy Render ketika push ke `main` selesai (setelah CI). 
- **Blueprint**: `render.yaml` disertakan; saat menghubungkan repo ke Render, pilih "Use render.yaml" agar worker dibuat otomatis.


### Channel/Thread auto-resolve & ensure
- Secara default, Nixe akan mencari **channel** bernama `log-botphising` dan **thread** bernama `imagephising`.
- Kamu bisa override dengan ENV **ID** atau **NAME**:
  - `PHISH_DB_CHANNEL_ID` **atau** `PHISH_DB_CHANNEL_NAME`
  - `PHISH_DB_THREAD_ID` **atau** `PHISH_DB_THREAD_NAME`
  - `MOD_LOG_CHANNEL_ID` **atau** `MOD_LOG_CHANNEL_NAME`
  - `LINK_DB_CHANNEL_ID` **atau** `LINK_DB_CHANNEL_NAME`
- Jika `AUTO_CREATE_DB_THREAD=1`, Nixe akan mencoba **membuat thread** `imagephising` di channel `log-botphising` bila belum ada (perlu izin Create Public Threads). Saat dibuat, Nixe akan **pin** template pHash dari `templates/pinned_phash_db_template.txt`.
# NixeBan
