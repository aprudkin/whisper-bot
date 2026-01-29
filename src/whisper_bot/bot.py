"""Telegram bot for voice message transcription."""

import asyncio
import logging
from pathlib import Path
from typing import Protocol

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from .config import config
from .groq_transcribe import transcribe_with_groq
from .llm_postprocess import postprocess_with_llm
from .groq_limits import GroqLimits

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(token=config.bot_token)
dp = Dispatcher()


class TranscriptionResult(Protocol):
    """Protocol for transcription result."""

    text: str


async def _transcribe(audio_path: Path) -> TranscriptionResult:
    """Transcribe audio using Groq API."""
    if not config.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is required")

    logger.info("Transcribing with Groq API (whisper-large-v3)")
    return await transcribe_with_groq(
        audio_path,
        config.groq_api_key,
        language=config.whisper_language,
    )


class MediaFile(Protocol):
    """Protocol for voice/video_note common interface."""

    file_id: str
    file_unique_id: str
    duration: int


async def _transcribe_media(
    message: Message,
    media: MediaFile,
    extension: str,
    media_type: str,
) -> None:
    """Download and transcribe media file, reply with result."""
    # Security: only process messages from allowed chats
    if not config.is_chat_allowed(message.chat.id):
        logger.warning(
            f"Ignored {media_type} from unauthorized chat {message.chat.id}"
        )
        return

    user = message.from_user
    username = user.username or f"id:{user.id}" if user else "unknown"
    logger.info(
        f"Received {media_type} from {username} "
        f"in chat {message.chat.id}, duration: {media.duration}s"
    )

    temp_path: Path | None = None
    try:
        file = await bot.get_file(media.file_id)
        if not file.file_path:
            await message.reply("Не удалось получить файл")
            return

        config.temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = config.temp_dir / f"{media.file_unique_id}.{extension}"
        await bot.download_file(file.file_path, temp_path)

        logger.info(f"Downloaded {media_type} to {temp_path}")

        result = await _transcribe(temp_path)
        text = result.text.strip()

        # LLM postprocessing for punctuation and spelling
        if text and config.enable_postprocess and config.groq_api_key:
            try:
                logger.info("Applying LLM postprocessing...")
                text = await postprocess_with_llm(text, config.groq_api_key)
            except Exception as e:
                logger.warning(f"Postprocess error: {e}, using raw transcription")

        if text:
            await message.reply(text)
            logger.info(f"Transcription sent: {len(text)} chars")
        else:
            await message.reply("(пустая запись)")

    except TelegramAPIError as e:
        logger.error(f"Telegram API error for {media_type}: {e}")
        await message.reply("Ошибка загрузки файла")
    except (OSError, RuntimeError) as e:
        logger.exception(f"Error processing {media_type}: {e}")
        await message.reply(f"Ошибка распознавания: {e}")

    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


@dp.message(F.voice)
async def handle_voice(message: Message) -> None:
    """Handle voice messages and reply with transcription."""
    if message.voice:
        await _transcribe_media(message, message.voice, "oga", "voice")


@dp.message(F.video_note)
async def handle_video_note(message: Message) -> None:
    """Handle video notes and reply with transcription."""
    if message.video_note:
        await _transcribe_media(message, message.video_note, "mp4", "video_note")


@dp.message(F.text.startswith("/status"))
async def handle_status(message: Message) -> None:
    """Show Groq API limits from last transcription request."""
    if not config.is_chat_allowed(message.chat.id):
        return

    if not config.groq_api_key:
        await message.reply("Groq API не настроен")
        return

    limits = GroqLimits.get_last()
    if limits:
        await message.reply(limits.format())
    else:
        await message.reply("Нет данных. Отправь голосовое сообщение, чтобы получить лимиты.")


async def _async_main() -> None:
    """Start the bot (async entry point)."""
    postprocess_status = "enabled" if config.enable_postprocess else "disabled"
    logger.info(
        f"Starting bot: Groq API (whisper-large-v3), "
        f"postprocess={postprocess_status}, "
        f"lang={config.whisper_language}, "
        f"allowed_chats={list(config.allowed_chats)}"
    )
    logger.info("Starting polling...")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


def main() -> None:
    """Start the bot (sync entry point for CLI)."""
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
