"""Check Groq API rate limits."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar
import httpx


@dataclass
class GroqLimits:
    """Groq API rate limit info from last request."""

    requests_limit: int  # RPD (requests per day)
    requests_remaining: int
    requests_reset: str
    audio_seconds_limit: int  # ASD (audio seconds per day)
    audio_seconds_remaining: int
    audio_seconds_reset: str
    updated_at: datetime = field(default_factory=datetime.now)

    # Singleton to store last known limits
    _last: ClassVar["GroqLimits | None"] = None

    def format(self) -> str:
        """Format limits for display."""
        age = (datetime.now() - self.updated_at).seconds
        age_str = f"{age} сек назад" if age < 60 else f"{age // 60} мин назад"

        return (
            f"📊 Groq Whisper Limits\n\n"
            f"Запросов в день: {self.requests_remaining:,} / {self.requests_limit:,}\n"
            f"Сброс: {self.requests_reset}\n\n"
            f"Аудио в день: {self.audio_seconds_remaining:,} / {self.audio_seconds_limit:,} сек\n"
            f"Сброс: {self.audio_seconds_reset}\n\n"
            f"🕐 Данные: {age_str}"
        )

    @classmethod
    def from_headers(cls, headers: httpx.Headers) -> "GroqLimits":
        """Parse limits from HTTP response headers."""
        limits = cls(
            requests_limit=int(headers.get("x-ratelimit-limit-requests", 0)),
            requests_remaining=int(headers.get("x-ratelimit-remaining-requests", 0)),
            requests_reset=headers.get("x-ratelimit-reset-requests", "unknown"),
            audio_seconds_limit=int(headers.get("x-ratelimit-limit-audio-seconds", 0)),
            audio_seconds_remaining=int(headers.get("x-ratelimit-remaining-audio-seconds", 0)),
            audio_seconds_reset=headers.get("x-ratelimit-reset-audio-seconds", "unknown"),
        )
        cls._last = limits
        return limits

    @classmethod
    def get_last(cls) -> "GroqLimits | None":
        """Get last known limits."""
        return cls._last
