"""
INERT STUB
----------
File ini sengaja DIKOSONGKAN agar lolos smoke check dan tidak membuat
pesan DB baru (BOARD/DB) secara otomatis.

Kalau kamu perlu membuat pesan DB teks **sekali saja**, gunakan CLI:
    python scripts/make_phash_db.py

ENV yang dipakai CLI:
  - DISCORD_TOKEN                 (wajib)
  - NIXE_PHASH_DB_THREAD_ID       (default: 1431192568221270108)
  - NIXE_PHASH_SOURCE_THREAD_ID   (default: 1409949797313679492)
  - PHASH_DB_MARKER               (default: NIXE_PHASH_DB_V1)
"""

from discord.ext import commands

async def setup(bot: commands.Bot):
    # Tidak mendaftarkan Cog apa pun. No-op by design.
    return
