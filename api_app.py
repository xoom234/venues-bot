"""HTTP API: Mini App, Telegram webhook, monthly reset."""

from __future__ import annotations

import json
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.utils.web_app import WebAppUser
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.routing import Route

import sheet
from bot import create_bot, create_dispatcher
from webapp_auth import AuthError, authenticate

log = logging.getLogger(__name__)

SHEET_DOWN = "Сервис временно недоступен"
MAX_TEXT = 500

_dp: Dispatcher | None = None


def _dispatcher() -> Dispatcher:
    global _dp
    if _dp is None:
        _dp = create_dispatcher()
    return _dp


def allowed_users() -> set[int]:
    raw = os.environ.get("ALLOWED_USERS", "")
    return {int(x.strip()) for x in raw.split(",") if x.strip()}


def allowed_usernames() -> set[str]:
    raw = os.environ.get("ALLOWED_USERNAMES", "")
    return {x.strip().lstrip("@").casefold() for x in raw.split(",") if x.strip()}


def norm(s: str) -> str:
    return " ".join(s.split()).casefold()


def show(value: str, empty: str = "не указано") -> str:
    return value if value else empty


def _user(request: Request) -> WebAppUser:
    user = authenticate(
        request.headers.get("authorization"),
        bot_token=os.environ["BOT_TOKEN"],
        allowed_user_ids=allowed_users(),
        allowed_usernames=allowed_usernames(),
    )
    request.scope["tg_user"] = user
    return user


def _venue_json(row: dict) -> dict:
    return {
        "row": row["row"],
        "name": row["name"],
        "status": row["status"],
        "aroma": row["aroma"],
        "format": row["format"],
    }


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"ok": True})


async def webhook_get(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


async def webhook_post(request: Request) -> Response:
    secret = os.environ.get("WEBHOOK_SECRET", "")
    got = request.headers.get("x-telegram-bot-api-secret-token", "")
    if not secret or got != secret:
        return Response(status_code=401)
    body = await request.body()
    bot = create_bot()
    try:
        update = Update.model_validate(json.loads(body), context={"bot": bot})
        await _dispatcher().feed_update(bot, update)
    except Exception:
        log.exception("webhook failed")
        return Response(status_code=500)
    finally:
        await bot.session.close()
    return Response(status_code=200)


async def cron_reset(request: Request) -> Response:
    secret = os.environ.get("CRON_SECRET", "")
    auth = request.headers.get("authorization", "")
    if not secret or auth != f"Bearer {secret}":
        return Response(status_code=401)
    try:
        cleared = sheet.clear_data()
    except Exception:
        log.exception("monthly reset failed")
        return Response(status_code=500)
    log.info("monthly reset: cleared %s rows", cleared)
    return JSONResponse({"ok": True, "cleared": cleared})


async def list_venues(request: Request) -> JSONResponse:
    _user(request)
    filt = (request.query_params.get("filter") or "all").casefold()
    query = norm(request.query_params.get("q") or "")
    try:
        rows = sheet.read_all()
    except Exception:
        log.exception("list_venues: таблица недоступна")
        return JSONResponse({"error": SHEET_DOWN}, status_code=503)

    items = []
    for r in rows:
        if not r["name"]:
            continue
        st = norm(r["status"])
        if filt == "passed" and st != "прошел":
            continue
        if filt == "failed" and st != "не прошел":
            continue
        if query and query not in norm(r["name"]):
            continue
        items.append(_venue_json(r))
    return JSONResponse({"items": items})


async def _notify(chat_id: int, text: str) -> None:
    try:
        async with Bot(token=os.environ["BOT_TOKEN"]) as bot:
            await bot.send_message(chat_id, text)
    except Exception:
        log.warning("Не удалось отправить подтверждение в чат %s", chat_id, exc_info=True)


def _text(payload: dict, key: str) -> str:
    value = payload.get(key)
    return value.strip() if isinstance(value, str) else ""


async def create_venue(request: Request) -> JSONResponse:
    user = _user(request)
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse({"error": "Тело запроса должно быть JSON"}, status_code=400)
    if not isinstance(payload, dict):
        return JSONResponse({"error": "Тело запроса должно быть JSON-объектом"}, status_code=400)

    name = " ".join(_text(payload, "name").split())
    if not name:
        return JSONResponse({"error": "Укажите название"}, status_code=422)
    if len(name) > MAX_TEXT:
        return JSONResponse({"error": "Слишком длинное название"}, status_code=422)

    try:
        rows = sheet.read_all()
        if any(norm(r["name"]) == norm(name) for r in rows):
            return JSONResponse({"error": f"Заведение «{name}» уже есть"}, status_code=409)
        sheet.add(name)
        rows = sheet.read_all()
        created = next(r for r in rows if norm(r["name"]) == norm(name))
    except Exception:
        log.exception("create_venue: таблица недоступна")
        return JSONResponse({"error": SHEET_DOWN}, status_code=503)

    log.info("uid=%s add %r (mini app)", user.id, name)
    await _notify(user.id, f"Добавлено через приложение: {name}")
    return JSONResponse(_venue_json(created), status_code=201)


async def update_venue(request: Request) -> JSONResponse:
    user = _user(request)
    try:
        row_num = int(request.path_params["row"])
    except (KeyError, ValueError, TypeError):
        return JSONResponse({"error": "Неверный номер строки"}, status_code=400)

    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse({"error": "Тело запроса должно быть JSON"}, status_code=400)
    if not isinstance(payload, dict):
        return JSONResponse({"error": "Тело запроса должно быть JSON-объектом"}, status_code=400)

    try:
        rows = sheet.read_all()
        venue = next((r for r in rows if r["row"] == row_num), None)
        if venue is None or not venue["name"]:
            return JSONResponse({"error": "Заведение не найдено"}, status_code=404)

        changes: list[str] = []

        if "status" in payload:
            status = _text(payload, "status")
            if status not in ("Прошел", "Не прошел", ""):
                return JSONResponse(
                    {"error": "Статус только «Прошел» или «Не прошел»"},
                    status_code=422,
                )
            old = venue["status"]
            sheet.update(row_num, 2, status)
            venue["status"] = status
            changes.append(f"статус «{show(old)}» → «{show(status)}»")

        if "aroma_append" in payload:
            text = _text(payload, "aroma_append")
            if not text:
                return JSONResponse({"error": "Текст аромата не может быть пустым"}, status_code=422)
            if len(text) > MAX_TEXT:
                return JSONResponse({"error": "Слишком длинный текст аромата"}, status_code=422)
            old = venue["aroma"]
            new = f"{old}, {text}" if old else text
            sheet.update(row_num, 3, new)
            venue["aroma"] = new
            changes.append(f"ароматы «{show(old)}» → «{new}»")

        if "format" in payload:
            text = _text(payload, "format")
            if not text:
                return JSONResponse({"error": "Текст формата не может быть пустым"}, status_code=422)
            if len(text) > MAX_TEXT:
                return JSONResponse({"error": "Слишком длинный текст формата"}, status_code=422)
            old = venue["format"]
            sheet.update(row_num, 4, text)
            venue["format"] = text
            changes.append(f"формат «{show(old)}» → «{text}»")

        if not changes:
            return JSONResponse({"error": "Нечего обновлять"}, status_code=422)
    except Exception:
        log.exception("update_venue: таблица недоступна")
        return JSONResponse({"error": SHEET_DOWN}, status_code=503)

    log.info("uid=%s update row=%s %s (mini app)", user.id, row_num, "; ".join(changes))
    await _notify(user.id, f"{venue['name']}: " + "; ".join(changes) + "\n(через приложение)")
    return JSONResponse(_venue_json(venue))


async def _auth_error(request: Request, exc: AuthError) -> JSONResponse:
    return JSONResponse({"error": exc.message}, status_code=exc.status)


async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
    log.exception("API error %s %s", request.method, request.url.path)
    return JSONResponse({"error": "Внутренняя ошибка сервера"}, status_code=500)


routes = [
    Route("/api/v1/health", health),
    Route("/api/v1/venues", list_venues, methods=["GET"]),
    Route("/api/v1/venues", create_venue, methods=["POST"]),
    Route("/api/v1/venues/{row:int}", update_venue, methods=["PATCH"]),
    Route("/api/webhook", webhook_get, methods=["GET"]),
    Route("/api/webhook", webhook_post, methods=["POST"]),
    Route("/api/cron_reset", cron_reset, methods=["GET", "POST"]),
]

app = Starlette(
    routes=routes,
    exception_handlers={
        AuthError: _auth_error,
        Exception: _unexpected,
    },
)
