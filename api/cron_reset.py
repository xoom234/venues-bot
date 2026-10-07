"""Vercel Cron: 2-го числа каждого месяца обнуляет данные таблицы."""

from __future__ import annotations

import json
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sheet

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def _authorized(handler: BaseHTTPRequestHandler) -> bool:
    secret = os.environ.get("CRON_SECRET", "")
    if not secret:
        return False
    auth = handler.headers.get("Authorization", "")
    return auth == f"Bearer {secret}"


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._run()

    def do_POST(self) -> None:
        self._run()

    def _run(self) -> None:
        if not _authorized(self):
            self.send_response(401)
            self.end_headers()
            return
        try:
            cleared = sheet.clear_data()
        except Exception:
            log.exception("monthly reset failed")
            self.send_response(500)
            self.end_headers()
            return
        log.info("monthly reset: cleared %s rows", cleared)
        body = json.dumps({"ok": True, "cleared": cleared}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        log.info("%s - %s", self.address_string(), format % args)
