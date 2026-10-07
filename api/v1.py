"""Vercel-функция: HTTP API для Telegram Mini App (/api/v1/*)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO)

from api_app import app  # noqa: E402,F401
