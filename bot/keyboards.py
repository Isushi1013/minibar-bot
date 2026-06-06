from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from bot.catalog import COFFEE_ITEMS, SIMPLE_ITEMS, TEA_ITEMS

CB_ADD = "a:"
CB_EDIT = "e:"
CB_ROOM = "r:"
CB_RECORD = "rec:"
CB_EDIT_ROOM = "er:"
CB_MENU = "m:"
CB_MAIN = "main"
CB_BACK = "back"
CB_LIST = "list"
CB_NOTHING = "nothing"
CB_SAVE = "save"
CB_SUBMIT = "submit"
CB_NEW = "new"
CB_UNDO = "undo"

BTN_LIST = "📝 Ввести номера"
BTN_EDIT_LIST = "✏️ Изменить список"
BTN_SUBMIT = "✅ Закрыть списания"
BTN_TOTALS = "📊 Итоги за сегодня"
BTN_YESTERDAY = "📅 Итоги за вчера"
BTN_BACK_MENU = "◀️ Главное меню"
BTN_BACK = "◀️ Назад"
BTN_UNDO = "↩ Отменить"
BTN_SAVE = "💾 Сохранить"
BTN_NOTHING = "➖ Ничего"
BTN_TEA = "☕ Чай"
BTN_COFFEE = "☕ Кофе"
BTN_SLIVKI = "🥛 Сливки"

ROOM_PREFIX = "Номер "
ROOM_DONE_PREFIX = "✅ Номер "
EDIT_PREFIX = "Изменить "


def _btn(label: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(label, callback_data=data)


def _reply(rows: list[list[str]]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        is_persistent=True,
        one_time_keyboard=False,
    )


# ─── Главное меню ────────────────────────────────────────────────────────────

def home_reply_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура главного меню: три кнопки."""
    return _reply([
        [BTN_LIST],
        [BTN_TOTALS, BTN_YESTERDAY],
    ])


# ─── Рабочий режим (после «Ввести номера») ───────────────────────────────────

def journal_reply_keyboard(
    pending_rooms: list[dict],
    planned_rooms: list[str],
) -> ReplyKeyboardMarkup:
    """Клавиатура в режиме работы с номерами."""
    rows: list[list[str]] = []

    room_labels = [
        *[f"{ROOM_PREFIX}{room}" for room in planned_rooms],
        *[f"{ROOM_DONE_PREFIX}{entry['room']}" for entry in pending_rooms],
    ]
    for i in range(0, len(room_labels), 3):
        rows.append(room_labels[i : i + 3])

    if pending_rooms:
        rows.append([BTN_SUBMIT])

    rows.append([BTN_BACK_MENU])

    return _reply(rows)


# ─── Inline-клавиатуры (без изменений) ───────────────────────────────────────

def journal_keyboard(
    pending_rooms: list[dict] | bool,
    planned_rooms: list[str] | None = None,
) -> InlineKeyboardMarkup:
    if isinstance(pending_rooms, bool):
        has_pending = pending_rooms
        pending_entries: list[dict] = []
    else:
        pending_entries = pending_rooms
        has_pending = bool(pending_entries)
    planned_entries = planned_rooms or []

    rows: list[list[InlineKeyboardButton]] = [
        [_btn("📝 Ввести список номеров", CB_LIST)]
    ]
    for i in range(0, len(planned_entries), 3):
        rows.append([
            _btn(str(room), f"{CB_ROOM}{i + offset}")
            for offset, room in enumerate(planned_entries[i : i + 3])
        ])
    for i, entry in enumerate(pending_entries):
        rows.append([_btn(f"✏️ Изменить {entry['room']}", f"{CB_EDIT}{i}")])
    if has_pending:
        rows.append([_btn("✅ Закрыть списания", CB_SUBMIT)])
    return InlineKeyboardMarkup(rows)


def main_keyboard(counts: dict[str, int]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for item in SIMPLE_ITEMS:
        n = counts.get(item.key, 0)
        suffix = f" ({n})" if n else ""
        row.append(_btn(f"{item.label}{suffix}", f"{CB_ADD}{item.key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([
        _btn("☕ Чай", f"{CB_MENU}tea"),
        _btn("☕ Кофе", f"{CB_MENU}coffee"),
    ])
    rows.append([_btn("↩ Отменить", CB_UNDO)])
    rows.append([_btn("💾 Сохранить номер", CB_SAVE)])
    rows.append([_btn("➖ Ничего", CB_NOTHING)])
    return InlineKeyboardMarkup(rows)


def submenu_keyboard(menu: str, counts: dict[str, int]) -> InlineKeyboardMarkup:
    items = {"tea": TEA_ITEMS, "coffee": COFFEE_ITEMS}[menu]
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for item in items:
        n = counts.get(item.key, 0)
        suffix = f" ({n})" if n else ""
        row.append(_btn(f"{item.label}{suffix}", f"{CB_ADD}{item.key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([_btn("💾 Сохранить номер", CB_SAVE)])
    rows.append([
        _btn("➖ Ничего", CB_NOTHING),
        _btn("◀️ Назад", CB_BACK),
    ])
    return InlineKeyboardMarkup(rows)


def room_action_keyboard(room: str, has_saved: bool) -> InlineKeyboardMarkup:
    rows = [[_btn("📝 Записать списание", f"{CB_RECORD}{room}")]]
    rows.append([_btn("🏠 В главное меню", CB_MAIN)])
    return InlineKeyboardMarkup(rows)


def _label_with_count(label: str, key: str, counts: dict[str, int]) -> str:
    n = counts.get(key, 0)
    return f"{label} ({n})" if n else label
