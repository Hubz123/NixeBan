"""
nixe/cogs/a00_fix_task_bootstrap_overlay.py
-------------------------------------------
Overlay kecil untuk memastikan task-loop pada cogs lain **baru start setelah bot login**.
Mengatasi error:
  RuntimeError: Client has not been properly initialised. Please use the login method...
yang terjadi bila `tasks.Loop.start()` dipanggil sebelum bot login.

Cara kerja:
- Saat `on_ready`, overlay ini mencari semua cogs yang punya atribut `discord.ext.tasks.Loop`.
- Untuk setiap loop yang **belum running**, overlay akan **start**-kan.
- Idempotent: aman dipanggil berulang, tidak mengubah cogs lain selain men-start loop sesudah bot siap.

Catatan:
- Solusi paling bersih tetap memperbaiki cog asal (panggil `.start()` di `on_ready` atau `cog_load` + gate `bot.is_ready()`).
- Overlay ini berguna bila kamu belum sempat edit cogs existing di zip lama.
"""

from __future__ import annotations
import inspect
from discord.ext import commands, tasks

TARGET_LOOP_ATTRS_HINT = {"_loop_collect", "_loop_watch", "_loop_sync"}  # hint umum, tapi overlay akan scan generik

class TaskBootstrapFix(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Scan semua cogs, cari tasks.Loop yang belum running, lalu start
        for name, cog in list(self.bot.cogs.items()):
            try:
                for attr in dir(cog):
                    obj = getattr(cog, attr, None)
                    if isinstance(obj, tasks.Loop):
                        if not obj.is_running():
                            try:
                                obj.start()
                            except RuntimeError:
                                # Bisa muncul kalau loop punya before_loop yang still menunggu ready;
                                # Tapi ini dipanggil setelah on_ready, jadi aman.
                                pass
            except Exception:
                # Jangan ganggu lifecycle bot jika ada satu cog bermasalah
                continue

async def setup(bot: commands.Bot):
    await bot.add_cog(TaskBootstrapFix(bot))
