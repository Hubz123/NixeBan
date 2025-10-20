"""
nixe/cogs/a00_graceful_shutdown.py
----------------------------------
Cog sederhana yang memasang graceful shutdown saat diload.
- Tidak memiliki command, tidak mengubah behavior bot selain penanganan SIGINT/SIGTERM.
- Aman dipakai berdampingan dengan cogs lain (idempotent).
"""

from __future__ import annotations
from discord.ext import commands
from nixe.helpers.graceful import install_graceful_shutdown

class _Null(commands.Cog):
    pass

async def setup(bot: commands.Bot):
    # Pasang graceful shutdown; tidak perlu hook tambahan.
    install_graceful_shutdown(bot, timeout=8.0, before_close=None)
    await bot.add_cog(_Null())
