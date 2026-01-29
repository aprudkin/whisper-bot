#!/bin/bash
set -e

echo "Starting whisper-bot..."
exec python -m whisper_bot.bot
