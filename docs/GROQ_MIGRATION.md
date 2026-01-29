# План перехода на Groq API

## Обзор

Groq предлагает бесплатный Whisper API с молниеносной скоростью inference.

### Преимущества Groq

| Параметр | faster-whisper (текущий) | Groq API |
|----------|--------------------------|----------|
| Скорость | ~5-7 сек на 5 сек аудио | **< 1 сек** |
| Модель | medium | **large-v3** (лучше качество) |
| Стоимость | Бесплатно (локально) | Бесплатно (20 req/min) |
| Зависимости | onnxruntime, ctranslate2 | Только httpx |
| Требования | RAM, CPU | Интернет |

## Шаги миграции

### 1. Получить API ключ

1. Зайти на [console.groq.com](https://console.groq.com)
2. Создать аккаунт (бесплатно)
3. Создать API ключ в разделе "API Keys"

### 2. Добавить в .env

```bash
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
TRANSCRIPTION_BACKEND=groq  # или "local" для faster-whisper
```

### 3. Создать Groq клиент

```python
# src/whisper_bot/groq_transcribe.py

import httpx
from pathlib import Path
from dataclasses import dataclass

GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


@dataclass
class TranscriptionResult:
    text: str
    language: str
    duration: float
    source_file: str


async def transcribe_with_groq(
    audio_path: Path,
    api_key: str,
    language: str = "ru",
) -> TranscriptionResult:
    """Transcribe audio using Groq API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        with open(audio_path, "rb") as f:
            response = await client.post(
                GROQ_API_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (audio_path.name, f, "audio/ogg")},
                data={
                    "model": "whisper-large-v3",
                    "language": language,
                    "response_format": "verbose_json",
                },
            )
        response.raise_for_status()
        data = response.json()

    return TranscriptionResult(
        text=data["text"],
        language=data.get("language", language),
        duration=data.get("duration", 0),
        source_file=audio_path.name,
    )
```

### 4. Обновить bot.py

```python
from .config import config

if config.transcription_backend == "groq":
    from .groq_transcribe import transcribe_with_groq as transcribe
else:
    from whisper_transcribe.core import transcribe_audio as transcribe
```

### 5. Обновить config.py

```python
@dataclass
class Config:
    bot_token: str
    groq_api_key: str | None = None
    transcription_backend: str = "local"  # "local" или "groq"
    whisper_model: str = "medium"
    whisper_language: str = "ru"
    whisper_device: str | None = None
    temp_dir: Path = Path("/tmp/whisper-bot")

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            bot_token=os.getenv("BOT_TOKEN"),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            transcription_backend=os.getenv("TRANSCRIPTION_BACKEND", "local"),
            # ... остальное
        )
```

## Лимиты Groq (бесплатный план)

| Лимит | Значение |
|-------|----------|
| Запросов в минуту | 20 |
| Запросов в день | 14,400 |
| Аудио файлов в день | 100 |
| Макс. размер файла | 25 MB |
| Макс. длительность | ~2 часа |

Для личного бота этого более чем достаточно.

## Fallback стратегия

При превышении лимитов Groq можно fallback на локальный faster-whisper:

```python
async def transcribe_with_fallback(audio_path: Path) -> TranscriptionResult:
    if config.groq_api_key:
        try:
            return await transcribe_with_groq(audio_path, config.groq_api_key)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limited
                logger.warning("Groq rate limited, falling back to local")
            else:
                raise

    # Fallback to local
    return await asyncio.to_thread(
        transcribe_audio,
        audio_path,
        model_name=config.whisper_model,
        language=config.whisper_language,
        device=config.whisper_device,
    )
```

## Сравнение времени ответа

| Сценарий | faster-whisper CPU | Groq API |
|----------|-------------------|----------|
| 5 сек голосовое | ~7 сек | ~1 сек |
| 30 сек голосовое | ~30 сек | ~2 сек |
| 1 мин голосовое | ~60 сек | ~3 сек |

## Когда мигрировать

Рекомендую мигрировать на Groq когда:
- Текущая скорость недостаточна
- Нужно лучшее качество (large-v3)
- Хочется уменьшить нагрузку на локальную машину

Текущий faster-whisper достаточно хорош для личного использования.
