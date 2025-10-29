# NIXE Quick Checklist (Gemini + Deploy)

## 1) Secrets (fill before run)
Edit **nixe/config/secrets.json**:
```json
{
  "NIXE_ALLOW_JSON_SECRETS": "1",
  "DISCORD_TOKEN": "<your_discord_bot_token>",
  "GEMINI_API_KEY": "<your_gemini_api_key>",
  "UPSTASH_REDIS_REST_URL": "<optional>",
  "UPSTASH_REDIS_REST_TOKEN": "<optional>"
}
```

- You can also use real environment variables instead of JSON. JSON works because `NIXE_ALLOW_JSON_SECRETS=1`.

## 2) Gemini model + thresholds
- Default model: `GEMINI_MODEL` in **nixe/config/runtime_env.json** (currently `gemini-2.5-flash`).
- Lucky pull decision threshold: `GEMINI_LUCKY_THRESHOLD` (e.g., `0.87`).
- Warmup: `GEMINI_WARMUP_ENABLE=1` with timeout `GEMINI_WARMUP_TIMEOUT_MS` (default 4000).

## 3) Lucky Pull guard channels
Set these in **nixe/config/runtime_env.json**:
- `LUCKYPULL_GUARD_CHANNELS` (comma-separated IDs or one ID)
- `LUCKYPULL_REDIRECT_CHANNEL_ID` (target channel)
- `LUCKYPULL_DELETE_ON_GUARD` → `"1"` if you want hard delete on guard
- `LUCKYPULL_MAX_LATENCY_MS` (budget, ms)

## 4) Local sanity checks
```bash
# syntax + structure only (no network, no heavy imports)
python scripts/smoke_all.py

# optional: import with lightweight stubs (still offline)
python scripts/smoke_all.py --strict-import
```

## 5) Run locally
```bash
pip install -r requirements.txt
python main.py
# Health: http://localhost:10000/healthz
```
