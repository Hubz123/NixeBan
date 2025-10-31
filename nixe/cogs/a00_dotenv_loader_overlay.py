# nixe/cogs/a00_dotenv_loader_overlay.py
"""
Early .env loader overlay (safe, no secret logging).

- Loads .env from project root and nixe/config/.env if present.
- Uses python-dotenv with override=False so existing OS env wins.
- Does not print any secret values.
"""
import logging, pathlib
from discord.ext import commands

class DotenvLoaderOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._load_dotenvs()

    def _load_dotenvs(self):
        try:
            from dotenv import load_dotenv
        except Exception:
            logging.getLogger(__name__).warning("[dotenv] python-dotenv not installed; skip .env loading")
            return
        root = pathlib.Path(__file__).resolve().parents[2]  # repo root
        candidates = [
            root / ".env",
            root / "nixe" / "config" / ".env",
        ]
        loaded = 0
        for p in candidates:
            try:
                if p.exists():
                    load_dotenv(dotenv_path=str(p), override=False)
                    loaded += 1
            except Exception:
                pass
        logging.getLogger(__name__).info("[dotenv] loaded %d .env file(s) (override=False)", loaded)

async def setup(bot):
    await bot.add_cog(DotenvLoaderOverlay(bot))
