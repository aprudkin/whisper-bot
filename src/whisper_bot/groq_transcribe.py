"""Groq API client for Whisper transcription."""

import httpx
from dataclasses import dataclass
from pathlib import Path

GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


@dataclass
class GroqTranscriptionResult:
    """Result from Groq transcription API."""

    text: str
    language: str
    duration: float
    source_file: str


async def transcribe_with_groq(
    audio_path: Path,
    api_key: str,
    language: str = "ru",
) -> GroqTranscriptionResult:
    """Transcribe audio using Groq Whisper API.

    Args:
        audio_path: Path to audio file (ogg, mp4, etc.)
        api_key: Groq API key
        language: Language code for transcription

    Returns:
        GroqTranscriptionResult with transcribed text and metadata

    Raises:
        httpx.HTTPStatusError: On API errors (including 429 rate limit)
    """
    # Determine content type and filename based on extension
    # Groq accepts: flac mp3 mp4 mpeg mpga m4a ogg opus wav webm
    ext = audio_path.suffix.lower()
    content_types = {
        ".oga": "audio/ogg",  # Telegram voice = Opus in Ogg container
        ".ogg": "audio/ogg",
        ".opus": "audio/opus",
        ".mp4": "video/mp4",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
        ".flac": "audio/flac",
    }
    content_type = content_types.get(ext, "audio/ogg")

    # Groq doesn't recognize .oga extension, rename to .ogg
    filename = audio_path.name
    if ext == ".oga":
        filename = audio_path.stem + ".ogg"

    async with httpx.AsyncClient(timeout=60.0) as client:
        with open(audio_path, "rb") as f:
            response = await client.post(
                GROQ_API_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (filename, f, content_type)},
                data={
                    "model": "whisper-large-v3",
                    "language": language,
                    "response_format": "json",
                },
            )
        if response.status_code != 200:
            # Log error details and raise with context
            import logging
            error_text = response.text
            logging.getLogger(__name__).error(
                f"Groq API error {response.status_code}: {error_text}"
            )
            response.raise_for_status()

        # Save rate limit info from headers
        from .groq_limits import GroqLimits
        GroqLimits.from_headers(response.headers)

        data = response.json()

    # json format returns only {"text": "..."}, verbose_json has more fields
    text = data["text"] if isinstance(data, dict) else data
    return GroqTranscriptionResult(
        text=text,
        language=language,
        duration=0,
        source_file=audio_path.name,
    )
