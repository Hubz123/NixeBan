
### Health endpoints (untuk UptimeRobot)
Nixe menyediakan HTTP health server (aiohttp) di `$PORT` (Render **Web Service**):
- `GET /healthz` → `200 OK` string `ok` (atau `starting` bila belum siap).  
  - Parameter `?full=1` mengembalikan JSON (uptime, guilds, entries DB).
  - Set `STRICT_HEALTH=1` jika ingin `503` selama belum siap (untuk alert ketat).
- `GET /readyz` → `200 OK` **hanya** kalau bot siap & DB pHash terload (`entries > 0`), selain itu `503`.

**Render:** ganti service ke **type: web** (lihat `render.yaml`) dan pastikan port otomatis (`$PORT`) digunakan oleh server.
