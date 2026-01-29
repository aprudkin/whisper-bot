#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$DIR/.venv/bin/python"
PID_FILE="$DIR/.bot.pid"
LOG_FILE="$DIR/bot.log"

if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
    echo "Bot already running (PID $(cat $PID_FILE))"
    exit 1
fi

nohup "$PYTHON" -m whisper_bot.bot >> "$LOG_FILE" 2>&1 &
PID=$!
echo $PID > "$PID_FILE"
echo "Bot starting (PID $PID), loading model..."

sleep 10
if kill -0 $PID 2>/dev/null; then
    echo "Bot running"
else
    echo "Bot failed to start, check logs"
    rm -f "$PID_FILE"
    exit 1
fi
