"""Telegram bot for voice message transcription."""

import asyncio
import logging
from pathlib import Path
from typing import Protocol

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from whisper_transcribe import get_device, transcribe_audio, get_model

from .config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(token=config.bot_token)
dp = Dispatcher()


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

        result = await asyncio.to_thread(
            transcribe_audio,
            temp_path,
            model_name=config.whisper_model,
            language=config.whisper_language,
            device=config.whisper_device,
        )

        if result.text.strip():
            await message.reply(result.text.strip())
            logger.info(f"Transcription sent: {len(result.text)} chars")
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


async def _async_main() -> None:
    """Start the bot (async entry point)."""
    device = config.whisper_device or get_device()
    logger.info(
        f"Starting bot with model={config.whisper_model}, "
        f"lang={config.whisper_language}, device={device}, "
        f"allowed_chats={list(config.allowed_chats)}"
    )

    logger.info("Preloading faster-whisper model...")
    await asyncio.to_thread(get_model, config.whisper_model, device)
    logger.info("Model loaded, starting polling...")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


def main() -> None:
    """Start the bot (sync entry point for CLI)."""
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
