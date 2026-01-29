#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$DIR/.bot.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "PID file not found"
    exit 1
fi

PID=$(cat "$PID_FILE")
if kill -0 $PID 2>/dev/null; then
    kill $PID
    rm "$PID_FILE"
    echo "Bot stopped (PID $PID)"
else
    echo "Process not running, cleaning up"
    rm "$PID_FILE"
fi
