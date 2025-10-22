
from __future__ import annotations
import os
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

log = logging.getLogger("nixe.config.env")

def load_dotenv_verbose() -> None:
    try:
        from dotenv import load_dotenv, find_dotenv
        path = find_dotenv(usecwd=True)
        if path:
            load_dotenv(path)
            print(f"✅ Loaded env file: {path}")
        else:
            env_path = os.path.join(os.getcwd(), ".env")
            if os.path.exists(env_path):
                load_dotenv(env_path)
                print(f"✅ Loaded env file: {env_path}")
    except Exception:
        return

@dataclass(frozen=True)
class Settings:
    MODE: str = os.getenv("NIXE_MODE", os.getenv("MODE", "production"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "10000"))
    LOG_CHANNEL_ID: Optional[int] = int(os.getenv("LOG_CHANNEL_ID")) if os.getenv("LOG_CHANNEL_ID") else None
    DISCORD_TOKEN: Optional[str] = (
        os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
    )
    RENDER_EXTERNAL_URL: Optional[str] = os.getenv("RENDER_EXTERNAL_URL")
    # No-spam toggle for uvicorn access log (default OFF)
    ACCESS_LOG: bool = os.getenv("ACCESS_LOG", "0") not in {"0", "false", "False"}

    def token(self) -> Optional[str]:
        return self.DISCORD_TOKEN

@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings()
