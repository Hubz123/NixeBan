# nixe/cogs/a16_lpg_persona_react_overlay.py
import os, logging, re, random, asyncio
from discord.ext import commands

YANDERE_LINES = [
    "Ketahuan ya~? Simpan gacha-mu di tempat yang benar atau... *aku* yang akan menyimpannya ❤️",
    "Lucky pull detected. Hush... di sini bukan tempatnya. Pergi sekarang sebelum aku *marah*~",
    "Hehe, keberuntunganmu manis. Tapi bukan di sini. Pindah sana, sebelum pedangku ikut bicara ✂️",
    "Awww, flex ya? Di channel terlarang? Geminiku bilang itu **lucky pull**. *Hapus* 😘",
    "Aku jagain server ini. Pamer boleh—**di channel yang benar**. Kali ini kubereskan dulu~"
]

def _env_bool(name: str, default=False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("1","true","yes","on","y")

class LPGPersonaReact(commands.Cog):
    """Emit persona lines when a lucky-pull deletion is logged by guards (LPA/legacy)."""
    PAT = re.compile(r"deleted a message in\s+(\d+).*\b(reason=)?lucky", re.I)

    def __init__(self, bot):
        self.bot = bot
        self.log = logging.getLogger(__name__)
        self.enabled = _env_bool("LPG_PERSONA_ENABLE", True)
        self._install_handler()

    def _install_handler(self):
        if not self.enabled:
            self.log.info("[lpg-persona] disabled by LPG_PERSONA_ENABLE=0")
            return
        parent = logging.getLogger()  # root
        handler = logging.Handler()
        handler.emit = self._on_log_emit
        parent.addHandler(handler)
        self.log.warning("[lpg-persona] persona react active (listening logs)")

    def _on_log_emit(self, record: logging.LogRecord):
        try:
            msg = record.getMessage()
        except Exception:
            return
        m = self.PAT.search(msg)
        if not m:
            return
        chan_id_str = m.group(1)
        try:
            chan_id = int(chan_id_str)
        except Exception:
            return
        # schedule send line
        asyncio.create_task(self._send_line(chan_id))

    async def _send_line(self, chan_id: int):
        await self.bot.wait_until_ready()
        ch = self.bot.get_channel(chan_id)
        if not ch:
            try:
                ch = await self.bot.fetch_channel(chan_id)
            except Exception:
                ch = None
        if not ch:
            return
        try:
            line = random.choice(YANDERE_LINES)
            await ch.send(line)
        except Exception as e:
            self.log.info(f"[lpg-persona] send failed: {e}")

async def setup(bot):
    await bot.add_cog(LPGPersonaReact(bot))
