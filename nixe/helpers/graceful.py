"""
nixe/helpers/graceful.py
------------------------
Utility untuk memasang graceful shutdown di discord.py bot.
- Menangani SIGINT/SIGTERM (Render/Unix/Windows fallback).
- Memanggil bot.close() lalu membatalkan task lain dan menunggu sebentar.
- Tidak mengubah arsitektur run kamu; bisa dipanggil dari cog saat setup().
"""

from __future__ import annotations
import asyncio
import signal
from typing import Optional, Awaitable, Callable

ShutdownHook = Optional[Callable[[], Awaitable[None]]]

_INSTALLED = False
_SHUTTING_DOWN = False

def install_graceful_shutdown(bot, *, timeout: float = 8.0, before_close: ShutdownHook = None) -> None:
    """
    Pasang handler SIGTERM/SIGINT untuk menutup bot secara rapi.
    - timeout: batas waktu menunggu task selesai.
    - before_close: coroutine opsional dipanggil sebelum bot.close().
    Aman dipanggil berulang (idempotent).
    """
    global _INSTALLED, _SHUTTING_DOWN
    if _INSTALLED:
        return
    _INSTALLED = True
    loop = asyncio.get_running_loop()

    async def _shutdown(reason: str) -> None:
        global _SHUTTING_DOWN
        if _SHUTTING_DOWN:
            return
        _SHUTTING_DOWN = True
        try:
            # Hook opsional sebelum close
            if before_close:
                try:
                    await asyncio.wait_for(before_close(), timeout=max(0.1, timeout/2))
                except Exception:
                    pass
            # Tutup bot (aman jika sudah tertutup)
            try:
                await bot.close()
            except Exception:
                pass
            # Batalkan task lain dan tunggu
            pending = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task(loop)]
            for t in pending:
                t.cancel()
            if pending:
                try:
                    await asyncio.wait_for(asyncio.gather(*pending, return_exceptions=True), timeout=timeout)
                except Exception:
                    pass
        except Exception:
            # Jangan biarkan exception menghambat shutdown
            pass

    def _handle(sig_name: str):
        try:
            loop.create_task(_shutdown(sig_name))
        except RuntimeError:
            # Loop mungkin sudah mati
            pass

    # Pasang handler signal
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle, sig.name)
        except (NotImplementedError, RuntimeError):
            # Fallback (Windows/embedded)
            try:
                signal.signal(sig, lambda *_: _handle(sig.name))
            except Exception:
                pass
