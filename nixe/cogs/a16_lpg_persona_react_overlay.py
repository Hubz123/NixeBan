# nixe/cogs/a16_lpg_persona_react_overlay.py
import os, logging, re, random, asyncio
from discord.ext import commands
from nixe.helpers.persona_loader import pick_line

def _env_bool(name: str, default=False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("1","true","yes","on","y")

class LPGPersonaReact(commands.Cog):
    """Emit YANDERE persona line from JSON when a lucky-pull deletion is logged by guards (LPA/legacy)."""
    PAT = re.compile(r"deleted a message in\s+(\d+).*(?:\b(reason=)?lucky)", re.I)

    def __init__(self, bot):
        self.bot = bot
        self.log = logging.getLogger(__name__)
        self.enabled = _env_bool("LPG_PERSONA_ENABLE", True)
        self.persona_name = os.getenv("LPG_PERSONA_NAME", "yandere")
        self.mode = os.getenv("LPG_PERSONA_MODE", "random")
        self._install_handler()

    def _install_handler(self):
        if not self.enabled:
            self.log.info("[lpg-persona] disabled by LPG_PERSONA_ENABLE=0")
            return
        parent = logging.getLogger()  # root
        handler = logging.Handler()
        handler.emit = self._on_log_emit
        parent.addHandler(handler)
        self.log.warning("[lpg-persona] persona react active (JSON source: %s, mode=%s)", self.persona_name, self.mode)

    def _on_log_emit(self, record: logging.LogRecord):
        try:
            msg = record.getMessage()
        except Exception:
            return
        m = self.PAT.search(msg)
        if not m:
            return
        try:
            chan_id = int(m.group(1))
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
            # Always source from JSON
            line = pick_line(self.persona_name, mode=self.mode, user="kamu", channel=f"<#{chan_id}>", reason="lucky pull")
            if not line:
                self.log.warning("[lpg-persona] persona JSON empty or missing groups for %s", self.persona_name)
                return
            await ch.send(line)
        except Exception as e:
            self.log.info(f"[lpg-persona] send failed: {e}")

async def setup(bot):
    await bot.add_cog(LPGPersonaReact(bot))
