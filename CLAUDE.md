# Whisper Bot - Project Index

## Overview

Telegram-бот для автоматической транскрипции голосовых сообщений в групповых чатах. Поддерживает два бэкенда:
- **Groq API** (рекомендуется) — whisper-large-v3, ~10x быстрее, бесплатно
- **Local** — faster-whisper (CTranslate2), работает офлайн

**Важно:** MPS (Apple Silicon GPU) **не поддерживается** локальным бэкендом — faster-whisper работает только на CPU/CUDA.

## Architecture

```
whisper-bot/
├── pyproject.toml              # Dependencies, entry points
├── Taskfile.yml                # go-task commands for bot management
├── .env.example                # Environment variables template
├── .env                        # Local config (git-ignored)
├── README.md                   # User documentation
├── CLAUDE.md                   # Project index (this file)
├── scripts/
│   ├── start.sh                # Background start with PID tracking
│   └── stop.sh                 # Graceful stop via SIGTERM
├── docs/
│   └── GROQ_MIGRATION.md       # Groq API migration documentation
└── src/whisper_bot/
    ├── __init__.py             # Package metadata (__version__)
    ├── config.py               # Configuration loading from .env
    ├── groq_transcribe.py      # Groq API client for transcription
    └── bot.py                  # Main bot logic (handlers, transcription)
```

## Key Components

### bot.py
- **Entry point**: `main()` → runs `_async_main()` via asyncio
- **Security**: Chat whitelist check at start of `_transcribe_media()`
- **Handlers**:
  - `handle_voice()` — processes voice messages (`.oga`)
  - `handle_video_note()` — processes round videos (`.mp4`)
- **Transcription**: `_transcribe_with_fallback()` — tries Groq first (if configured), falls back to local on rate limit (429)
- **Flow**: Check allowed chat → Download → Transcribe (Groq/local) → Reply → Cleanup

### groq_transcribe.py
- Async Groq API client using httpx
- Uses `whisper-large-v3` model for best quality
- Supports multiple audio formats (ogg, mp4, mp3, wav, m4a)

### config.py
- Loads from `.env` via python-dotenv
- `Config` dataclass with fields:
  - `bot_token: str` — Telegram bot token (required)
  - `allowed_chats: frozenset[int]` — Whitelist of chat IDs (required)
  - `groq_api_key: str | None` — Groq API key (required if backend=groq)
  - `transcription_backend: str` — "local" or "groq" (default: local)
  - `whisper_model: str` — Model size for local backend (default: `medium`)
  - `whisper_language: str` — Language code (default: `ru`)
  - `whisper_device: str | None` — Device override (default: auto-detect)
  - `temp_dir: Path` — Temp files location (default: `/tmp/whisper-bot`)
- Method `is_chat_allowed(chat_id)` for security check

## Dependencies

```toml
dependencies = [
    "aiogram>=3.0",           # Telegram Bot API (async)
    "python-dotenv>=1.0",     # .env loading
    "httpx>=0.24",            # Async HTTP client for Groq API
    "whisper-transcribe",     # Local package from ../whisper-cli
]
```

**Transitive (from whisper-transcribe):**
- `faster-whisper` — CTranslate2-based Whisper implementation
- `ctranslate2` — Optimized inference engine (CPU/CUDA only, no MPS)

## Task Commands

| Command | Description |
|---------|-------------|
| `task start` | Start bot in background |
| `task stop` | Stop bot |
| `task restart` | Restart bot |
| `task status` | Show running status |
| `task logs` | Tail logs (live) |
| `task logs:last` | Last 50 log lines |
| `task logs:clear` | Clear log file |
| `task install` | Install dependencies |
| `task env` | Create .env from template |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | Yes | — | Telegram bot token from @BotFather |
| `ALLOWED_CHATS` | Yes | — | Comma-separated chat IDs (e.g., `-1001234567890,-1009876543210`) |
| `TRANSCRIPTION_BACKEND` | No | `local` | Backend: `local` (faster-whisper) or `groq` (Groq API) |
| `GROQ_API_KEY` | If groq | — | Groq API key from console.groq.com |
| `WHISPER_MODEL` | No | `medium` | Model for local backend: tiny/base/small/medium/large/large-v2/large-v3 |
| `WHISPER_LANGUAGE` | No | `ru` | Recognition language |
| `WHISPER_DEVICE` | No | cpu | Device for local: cpu/cuda (MPS not supported) |

## Whisper Models Comparison

| Model | Size | Quality (RU) | Speed (30s audio, CPU) |
|-------|------|--------------|------------------------|
| tiny | 39MB | Low | ~3s |
| base | 74MB | Basic | ~5s |
| small | 244MB | Good | ~10s |
| **medium** | 769MB | Excellent | ~15s |
| large-v3 | 1.5GB | Best | ~30s |

**Recommendation:** `medium` — best quality/speed balance for Russian.

## Development Notes

- Bot uses `asyncio.to_thread()` to run sync Whisper in thread pool (non-blocking)
- Temp files stored in `/tmp/whisper-bot/`, cleaned after processing
- Model preloaded on startup to avoid first-message latency
- No Docker — runs natively on host
- Taskfile uses mvdan/sh interpreter — use `/bin/kill` instead of `kill` builtin
- Security: bot only responds in chats listed in `ALLOWED_CHATS`
- **MPS not available** — faster-whisper/CTranslate2 doesn't support Apple Silicon GPU

## Groq API (Recommended)

Бот поддерживает Groq API как основной бэкенд транскрипции:

| Параметр | Local (faster-whisper) | Groq API |
|----------|------------------------|----------|
| Скорость | ~15-30 сек | **< 2 сек** |
| Модель | medium | **large-v3** (лучше качество) |
| Стоимость | Бесплатно (локально) | Бесплатно (20 req/min) |
| Требования | RAM, CPU | Только интернет |

**Лимиты Groq (бесплатный план):**
- 20 запросов/минуту
- 14,400 запросов/день
- 25 MB макс. размер файла

При превышении лимита бот автоматически переключается на локальный whisper.
