"""Bot configuration from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

VALID_MODELS = frozenset({"tiny", "base", "small", "medium", "large", "large-v2", "large-v3"})
VALID_DEVICES = frozenset({"cpu", "cuda"})


@dataclass
class Config:
    """Bot configuration."""

    bot_token: str
    allowed_chats: frozenset[int]
    whisper_model: str = "medium"
    whisper_language: str = "ru"
    whisper_device: str | None = None  # None = auto-detect, "cpu", "cuda"
    temp_dir: Path = Path("/tmp/whisper-bot")

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not self.allowed_chats:
            raise ValueError(
                "ALLOWED_CHATS environment variable is required. "
                "Specify comma-separated chat IDs (e.g., -1001234567890,-1009876543210)"
            )
        if self.whisper_model not in VALID_MODELS:
            raise ValueError(
                f"Invalid whisper_model '{self.whisper_model}'. "
                f"Valid options: {', '.join(sorted(VALID_MODELS))}"
            )
        if self.whisper_device and self.whisper_device not in VALID_DEVICES:
            raise ValueError(
                f"Invalid whisper_device '{self.whisper_device}'. "
                f"Valid options: {', '.join(sorted(VALID_DEVICES))}"
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

        device = os.getenv("WHISPER_DEVICE")
        if device == "auto":
            device = None

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
            allowed_chats=allowed_chats,
            whisper_model=os.getenv("WHISPER_MODEL", "medium"),
            whisper_language=os.getenv("WHISPER_LANGUAGE", "ru"),
            whisper_device=device,
        )


config = Config.from_env()
