"""Bot configuration from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Bot configuration."""

    bot_token: str
    groq_api_key: str
    allowed_chats: frozenset[int]
    whisper_language: str = "ru"
    enable_postprocess: bool = False  # LLM-based punctuation and spelling correction
    temp_dir: Path = Path("/tmp/whisper-bot")

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not self.allowed_chats:
            raise ValueError(
                "ALLOWED_CHATS environment variable is required. "
                "Specify comma-separated chat IDs (e.g., -1001234567890,-1009876543210)"
            )

    def is_chat_allowed(self, chat_id: int) -> bool:
        """Check if chat is in the allowed list."""
        return chat_id in self.allowed_chats

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        token = os.getenv("BOT_TOKEN")
        if not token:
            raise ValueError("BOT_TOKEN environment variable is required")

        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise ValueError("GROQ_API_KEY environment variable is required")

        # Parse allowed chats from comma-separated list
        allowed_chats_str = os.getenv("ALLOWED_CHATS", "")
        allowed_chats: frozenset[int] = frozenset()
        if allowed_chats_str.strip():
            try:
                allowed_chats = frozenset(
                    int(chat_id.strip())
                    for chat_id in allowed_chats_str.split(",")
                    if chat_id.strip()
                )
            except ValueError as e:
                raise ValueError(
                    f"Invalid ALLOWED_CHATS format. Use comma-separated integers: {e}"
                ) from e

        return cls(
            bot_token=token,
            groq_api_key=groq_key,
            allowed_chats=allowed_chats,
            whisper_language=os.getenv("WHISPER_LANGUAGE", "ru"),
            enable_postprocess=os.getenv("ENABLE_POSTPROCESS", "").lower() in ("true", "1", "yes"),
        )


config = Config.from_env()
