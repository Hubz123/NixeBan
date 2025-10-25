# pHash DB CLI (manual)
Gunakan CLI ini **hanya saat perlu** membuat pHash DB teks secara manual.

## Persiapan ENV
```
export DISCORD_TOKEN=...                     # token bot
export NIXE_FORCE_DB_CLI=1                  # safety gate
export NIXE_PHASH_DB_THREAD_ID=1431192568221270108
export NIXE_PHASH_SOURCE_THREAD_ID=1409949797313679492
export PHASH_DB_MARKER=NIXE_PHASH_DB_V1
```

## Jalankan
```
python tools/make_phash_db_cli.py --yes
```

CLI akan mengadopsi pesan DB yang sudah ada (marker sama) atau membuat baru
(**pesan teks**, bukan embed) lalu mencoba pin.
