
from __future__ import annotations
import os
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

log = logging.getLogger("nixe.config.env")

# Optional .env loader (no hard dependency)
def load_dotenv_verbose() -> None:
    """Load .env if python-dotenv is available and log the path like original."""
    try:
        from dotenv import load_dotenv, find_dotenv
        path = find_dotenv(usecwd=True)
        if path:
            load_dotenv(path)
            print(f"✅ Loaded env file: {path}")
        else:
            # Still print something to match expectation
            env_path = os.path.join(os.getcwd(), ".env")
            if os.path.exists(env_path):
                load_dotenv(env_path)
                print(f"✅ Loaded env file: {env_path}")
    except Exception:
        # Silent if dotenv not installed
        return

@dataclass(frozen=True)
class Settings:
    MODE: str = os.getenv("NIXE_MODE", os.getenv("MODE", "production"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "10000"))
    LOG_CHANNEL_ID: Optional[int] = int(os.getenv("LOG_CHANNEL_ID")) if os.getenv("LOG_CHANNEL_ID") else None
    ACCESS_LOG: bool = os.getenv("ACCESS_LOG", "0") not in {"0", "false", "False"}
    # Discord tokens (multiple env names supported)
    DISCORD_TOKEN: Optional[str] = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
    # Extra
    RENDER_EXTERNAL_URL: Optional[str] = os.getenv("RENDER_EXTERNAL_URL")

    def token(self) -> Optional[str]:
        return self.DISCORD_TOKEN

@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings()
