"""Работа с Google Таблицей «Заведения»: чтение, поиск, обновление, добавление."""

import json
import os

import gspread

SHEET_NAME = "Заведения"

COL_NAME = 0
COL_STATUS = 1
COL_AROMA = 2
COL_FORMAT = 3


def _client():
    raw = os.environ["GOOGLE_CREDENTIALS"].strip()
    if raw.startswith("{"):
        return gspread.service_account_from_dict(json.loads(raw))
    return gspread.service_account(filename=raw)


def _worksheet():
    return _client().open_by_key(os.environ["SPREADSHEET_ID"]).worksheet(SHEET_NAME)


def read_all() -> list[dict]:
    """Все строки таблицы (без шапки)."""
    rows = _worksheet().get_all_values()
    result = []
    for i, row in enumerate(rows[1:], start=2):
        padded = row + [""] * (4 - len(row))
        result.append(
            {
                "row": i,
                "name": padded[COL_NAME],
                "status": padded[COL_STATUS],
                "aroma": padded[COL_AROMA],
                "format": padded[COL_FORMAT],
            }
        )
    return result


def find(name: str) -> list[dict]:
    """Поиск заведений по названию (без учёта регистра и лишних пробелов)."""
    needle = " ".join(name.split()).casefold()
    return [r for r in read_all() if needle in " ".join(r["name"].split()).casefold()]


def update(row: int, column: int, value: str) -> None:
    """Обновить ячейку. column: 1=название, 2=статус, 3=ароматы, 4=формат."""
    _worksheet().update_cell(row, column, value)


def add(name: str) -> None:
    """Добавить новое заведение с пустыми остальными колонками."""
    _worksheet().append_row([name, "", "", ""], value_input_option="USER_ENTERED")


def clear_data() -> int:
    """Обнулить статус, ароматы и формат. Названия заведений не трогает. Возвращает число строк."""
    ws = _worksheet()
    rows = ws.get_all_values()
    n = max(0, len(rows) - 1)
    if n == 0:
        return 0
    ws.batch_clear([f"B2:D{n + 1}"])
    return n
