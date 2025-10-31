# Lucky Pull Provider Patch (Gemini → Groq fallback)

Date: 2025-10-31T05:20:30

What changed:
- **Persistent circuit-breaker** for Gemini 429 in `nixe/helpers/gemini_bridge.py`:
  - On 429, Gemini is **blocked** and the block is saved to `nixe/tmp/gemini_gate.json`.
  - Every classification call and warmup can **health-check** Gemini and **re-enable** automatically when the API responds (no 429).
- **Groq vision fallback** is used whenever Gemini is blocked or fails.
- Added **async wrapper** `classify_lucky_pull(images, hints, timeout_ms)` for compatibility with `LuckyPullGuard`.
- Provider defaults enforced:
  - `GEMINI_MODEL=gemini-2.5-flash-lite`
  - `GROQ_MODEL_VISION_CANDIDATES=llama-3.2-90b-vision,llama-3.2-11b-vision`
  - Template env includes `GROQ_MODEL=llama-3.1-8b-instant` (for QnA), and `LPG_GEM_429_COOLDOWN_SEC=600`.
- No behavior change to delete/redirect policy—only the provider selection & stability.

How it works now:
1. Try **Gemini** (if not blocked). On 429 → put Gemini on **cooldown** (file-backed) and continue.
2. Try **Groq Vision** (llama-3.2-90b/11b). If it succeeds, result is used. If both fail and `LPG_FAIL_CLOSE=0`, we **do not delete**.
3. A lightweight **health-check** runs opportunistically to lift the cooldown once Gemini is healthy again.

Where to tweak:
- `LPG_GEM_429_COOLDOWN_SEC` to change the minimum block duration (default 600s).
- Set `GROQ_MODEL_VISION` to pin a specific Groq model outright.
- `GROQ_MODEL_VISION_CANDIDATES` to control the fallback scan order.

