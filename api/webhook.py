"""Vercel serverless: Telegram webhook."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aiogram import Bot, Dispatcher
from aiogram.types import Update

from bot import create_bot, create_dispatcher

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

_bot: Bot | None = None
_dp: Dispatcher | None = None


def _app() -> tuple[Bot, Dispatcher]:
    global _bot, _dp
    if _bot is None or _dp is None:
        _bot = create_bot()
        _dp = create_dispatcher()
    return _bot, _dp


async def _handle(body: bytes) -> None:
    bot, dp = _app()
    update = Update.model_validate(json.loads(body), context={"bot": bot})
    await dp.feed_update(bot, update)


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ok")

    def do_POST(self) -> None:
        secret = os.environ.get("WEBHOOK_SECRET", "")
        got = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not secret or got != secret:
            self.send_response(401)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            asyncio.run(_handle(body))
        except Exception:
            log.exception("webhook failed")
            self.send_response(500)
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:
        log.info("%s - %s", self.address_string(), format % args)
