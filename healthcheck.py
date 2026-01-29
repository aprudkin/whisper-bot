#!/usr/bin/env python3
"""Healthcheck script for Docker container."""

import subprocess
import sys


def main() -> int:
    """Check if bot process is running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "whisper_bot"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return 0
        print("Bot process not found")
        return 1
    except Exception as e:
        print(f"Healthcheck error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
