"""Обработчики команд бота и проверка доступа."""

import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import BaseFilter, Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

import sheet

log = logging.getLogger(__name__)

SHEET_DOWN = "Сервис временно недоступен"
DEFAULT_WEBAPP_URL = "https://venues-bot.vercel.app/"


def webapp_url() -> str:
    return os.environ.get("WEBAPP_URL", "").strip() or DEFAULT_WEBAPP_URL


def open_app_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть заведения", web_app=WebAppInfo(url=webapp_url()))]
        ]
    )


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


class AccessFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        user = message.from_user
        if user and user.id in allowed_users():
            return True
        uname = (user.username or "").casefold() if user else ""
        if uname and uname in allowed_usernames():
            return True
        await message.answer("Нет доступа")
        return False


def resolve(query: str) -> dict | str:
    """Одно заведение или текст ошибки."""
    matches = sheet.find(query)
    if not matches:
        return "Заведение не найдено. Смотри список: /list"
    exact = [m for m in matches if norm(m["name"]) == norm(query)]
    if len(exact) == 1:
        return exact[0]
    if len(matches) == 1:
        return matches[0]
    names = ", ".join(m["name"] for m in matches)
    return f"Найдено несколько заведений: {names}. Уточни название."


def parse_set(args: str) -> tuple[str, str] | str:
    """(название, статус_для_таблицы) или текст ошибки."""
    text = " ".join(args.split())
    if not text:
        return "Неверный формат. Пример: /set HookahPlace прошел"
    low = text.casefold()
    if low.endswith("не прошел"):
        name = text[: -len("не прошел")].strip()
        status = "Не прошел"
    elif low.endswith("прошел"):
        name = text[: -len("прошел")].strip()
        status = "Прошел"
    else:
        return "Статус только «прошел» или «не прошел». Пример: /set HookahPlace прошел"
    if not name:
        return "Неверный формат. Пример: /set HookahPlace прошел"
    return name, status


def parse_venue_text(args: str) -> tuple[dict, str] | str:
    """Самое длинное точное совпадение названия в начале + остаток текста."""
    text = " ".join(args.split())
    if not text:
        return "Неверный формат"
    args_n = norm(text)
    best: list[dict] = []
    best_len = 0
    for row in sheet.read_all():
        name_n = norm(row["name"])
        if not name_n:
            continue
        if args_n == name_n or args_n.startswith(name_n + " "):
            if len(name_n) > best_len:
                best = [row]
                best_len = len(name_n)
            elif len(name_n) == best_len:
                best.append(row)
    if not best:
        return "Заведение не найдено. Смотри список: /list"
    if len(best) > 1:
        names = ", ".join(m["name"] for m in best)
        return f"Найдено несколько заведений: {names}. Уточни название."
    venue = best[0]
    n_tokens = len(norm(venue["name"]).split())
    rest = " ".join(text.split()[n_tokens:])
    return venue, rest


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    access = AccessFilter()

    @dp.message(Command("start"), access)
    async def cmd_start(message: Message) -> None:
        await message.answer(
            "Заведения: список, статус, ароматы и формат.\n\n"
            "Нажмите «Открыть заведения» или используйте команды из /help.",
            reply_markup=open_app_keyboard(),
        )

    @dp.message(Command("help"), access)
    async def cmd_help(message: Message) -> None:
        await message.answer(
            "Команды:\n"
            "/list — все заведения\n"
            "/info <заведение> — строка\n"
            "/passed — прошедшие\n"
            "/failed — не прошедшие\n"
            "/set <заведение> <прошел|не прошел>\n"
            "/aroma <заведение> <текст>\n"
            "/format <заведение> <текст>\n"
            "/add <название>\n\n"
            "Или откройте приложение: /start"
        )

    @dp.message(Command("list"), access)
    async def cmd_list(message: Message) -> None:
        try:
            rows = sheet.read_all()
        except Exception:
            log.exception("list: таблица недоступна")
            await message.answer(SHEET_DOWN)
            return
        lines = [f"{r['name']}: {show(r['status'], 'не задан')}" for r in rows if r["name"]]
        await message.answer("\n".join(lines) if lines else "Таблица пуста")

    @dp.message(Command("info"), access)
    async def cmd_info(message: Message, command: CommandObject) -> None:
        args = (command.args or "").strip()
        if not args:
            await message.answer("Неверный формат. Пример: /info Дуть")
            return
        try:
            found = resolve(args)
        except Exception:
            log.exception("info: таблица недоступна")
            await message.answer(SHEET_DOWN)
            return
        if isinstance(found, str):
            await message.answer(found)
            return
        await message.answer(
            f"Заведение: {found['name']}\n"
            f"Статус: {show(found['status'])}\n"
            f"Ароматы: {show(found['aroma'])}\n"
            f"Формат: {show(found['format'])}"
        )

    @dp.message(Command("passed"), access)
    async def cmd_passed(message: Message) -> None:
        try:
            rows = sheet.read_all()
        except Exception:
            log.exception("passed: таблица недоступна")
            await message.answer(SHEET_DOWN)
            return
        lines = [r["name"] for r in rows if norm(r["status"]) == "прошел"]
        await message.answer("\n".join(lines) if lines else "Нет заведений со статусом «прошел»")

    @dp.message(Command("failed"), access)
    async def cmd_failed(message: Message) -> None:
        try:
            rows = sheet.read_all()
        except Exception:
            log.exception("failed: таблица недоступна")
            await message.answer(SHEET_DOWN)
            return
        lines = [r["name"] for r in rows if norm(r["status"]) == "не прошел"]
        await message.answer("\n".join(lines) if lines else "Нет заведений со статусом «не прошел»")

    @dp.message(Command("set"), access)
    async def cmd_set(message: Message, command: CommandObject) -> None:
        parsed = parse_set(command.args or "")
        if isinstance(parsed, str):
            await message.answer(parsed)
            return
        name, status = parsed
        try:
            found = resolve(name)
            if isinstance(found, str):
                await message.answer(found)
                return
            old = found["status"]
            sheet.update(found["row"], 2, status)
        except Exception:
            log.exception("set: таблица недоступна")
            await message.answer(SHEET_DOWN)
            return
        uid = message.from_user.id if message.from_user else "?"
        log.info("uid=%s set %s: %r → %r", uid, found["name"], old, status)
        await message.answer(
            f"{found['name']}: статус «{show(old)}» → «{status}»"
        )

    @dp.message(Command("aroma"), access)
    async def cmd_aroma(message: Message, command: CommandObject) -> None:
        args = (command.args or "").strip()
        if not args:
            await message.answer("Неверный формат. Пример: /aroma Art Lounge манго, мята")
            return
        try:
            parsed = parse_venue_text(args)
            if isinstance(parsed, str):
                await message.answer(
                    parsed if parsed != "Неверный формат"
                    else "Неверный формат. Пример: /aroma Art Lounge манго, мята"
                )
                return
            venue, text = parsed
            if not text:
                await message.answer("Текст не может быть пустым. Пример: /aroma Art Lounge манго, мята")
                return
            old = venue["aroma"]
            new = f"{old}, {text}" if old else text
            sheet.update(venue["row"], 3, new)
        except Exception:
            log.exception("aroma: таблица недоступна")
            await message.answer(SHEET_DOWN)
            return
        uid = message.from_user.id if message.from_user else "?"
        log.info("uid=%s aroma %s: %r → %r", uid, venue["name"], old, new)
        await message.answer(
            f"{venue['name']}: ароматы «{show(old)}» → «{new}»"
        )

    @dp.message(Command("format"), access)
    async def cmd_format(message: Message, command: CommandObject) -> None:
        args = (command.args or "").strip()
        if not args:
            await message.answer("Неверный формат. Пример: /format Jack Lounge день рождения")
            return
        try:
            parsed = parse_venue_text(args)
            if isinstance(parsed, str):
                await message.answer(
                    parsed if parsed != "Неверный формат"
                    else "Неверный формат. Пример: /format Jack Lounge день рождения"
                )
                return
            venue, text = parsed
            if not text:
                await message.answer(
                    "Текст не может быть пустым. Пример: /format Jack Lounge день рождения"
                )
                return
            old = venue["format"]
            sheet.update(venue["row"], 4, text)
        except Exception:
            log.exception("format: таблица недоступна")
            await message.answer(SHEET_DOWN)
            return
        uid = message.from_user.id if message.from_user else "?"
        log.info("uid=%s format %s: %r → %r", uid, venue["name"], old, text)
        await message.answer(
            f"{venue['name']}: формат «{show(old)}» → «{text}»"
        )

    @dp.message(Command("add"), access)
    async def cmd_add(message: Message, command: CommandObject) -> None:
        name = " ".join((command.args or "").split())
        if not name:
            await message.answer("Неверный формат. Пример: /add Новый Лаунж")
            return
        try:
            rows = sheet.read_all()
            if any(norm(r["name"]) == norm(name) for r in rows):
                await message.answer(f"Заведение «{name}» уже есть")
                return
            sheet.add(name)
        except Exception:
            log.exception("add: таблица недоступна")
            await message.answer(SHEET_DOWN)
            return
        uid = message.from_user.id if message.from_user else "?"
        log.info("uid=%s add %r", uid, name)
        await message.answer(f"Добавлено: {name}")

    return dp


def create_bot() -> Bot:
    token = os.environ["BOT_TOKEN"]
    if not token:
        raise RuntimeError("BOT_TOKEN пуст — вставь токен в .env")
    return Bot(token=token)
