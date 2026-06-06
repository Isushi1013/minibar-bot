import re
from datetime import date, timedelta
from telegram import InputFile, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.catalog import (
    ALL_ITEMS,
    COFFEE_KEYS,
    DISPLAY_ORDER,
    TEA_KEYS,
    category_limit,
    category_total,
)
from bot.formatters import format_journal, format_submit_confirmation, format_summary
from bot.html_export import write_html_export, write_text_export
from bot.keyboards import (
    BTN_BACK_MENU,
    BTN_EDIT_LIST,
    BTN_LIST,
    BTN_SUBMIT,
    BTN_TOTALS,
    BTN_YESTERDAY,
    CB_ADD,
    CB_BACK,
    CB_EDIT,
    CB_EDIT_ROOM,
    CB_LIST,
    CB_MAIN,
    CB_MENU,
    CB_NOTHING,
    CB_RECORD,
    CB_ROOM,
    CB_SAVE,
    CB_SUBMIT,
    CB_UNDO,
    ROOM_DONE_PREFIX,
    ROOM_PREFIX,
    home_reply_keyboard,
    journal_reply_keyboard,
    main_keyboard,
    room_action_keyboard,
    submenu_keyboard,
)
from bot.session import (
    add_pending_room,
    clear_pending,
    get_session,
    push_history,
    reset_current_room,
    reset_session,
    replace_room_list,
    set_room_list,
    set_journal_message,
    start_edit_room,
    start_room_from_plan,
)
from bot.storage import append_batch, get_daily_totals, load_history

WELCOME_TEXT = (
    "👋 Привет! Я бот списаний мини-бара.\n\n"
    "Выбери действие:"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reset_session(context)
    await update.effective_message.reply_text(
        WELCOME_TEXT,
        reply_markup=home_reply_keyboard(),
    )


async def handle_room_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    session = get_session(context)

    # ─── Главное меню ────────────────────────────────────────────

    if text == BTN_TOTALS:
        await _send_totals(update, context, target_date=date.today(), label="Итоги за сегодня")
        return

    if text == BTN_YESTERDAY:
        yesterday = date.today() - timedelta(days=1)
        await _send_totals(update, context, target_date=yesterday, label="Итоги за вчера")
        return

    if text == BTN_BACK_MENU:
        # Возврат в главное меню — сбрасываем сессию
        if session.get("room"):
            await update.message.reply_text(
                "Сначала сохрани или отмени текущий номер.",
                reply_markup=_journal_reply_markup(context),
            )
            return
        reset_session(context)
        await update.message.reply_text(WELCOME_TEXT, reply_markup=home_reply_keyboard())
        return

    # ─── Переход в рабочий режим ─────────────────────────────────

    if text == BTN_LIST:
        session["awaiting_room_list"] = True
        session["editing_room_list"] = False
        session["work_mode"] = True
        await update.message.reply_text(
            "Отправь список номеров одним сообщением: через пробел, запятую или с новой строки.",
            reply_markup=_journal_reply_markup(context),
        )
        return

    # ─── Рабочий режим ───────────────────────────────────────────

    if text == BTN_EDIT_LIST:
        session["awaiting_room_list"] = True
        session["editing_room_list"] = True
        await update.message.reply_text(
            "Отправь новый список номеров.",
            reply_markup=_journal_reply_markup(context),
        )
        return

    if text == BTN_SUBMIT:
        await _submit_batch_from_message(update, context)
        return

    if session.get("room") is not None:
        await update.message.reply_text(
            "Сначала сохрани текущий номер кнопками под сообщением.",
            reply_markup=_journal_reply_markup(context),
        )
        return

    room = _room_from_button_text(text)
    if room is not None:
        has_saved = _pending_room_index(session, room) is not None
        has_planned = _planned_room_index(session, room) is not None
        if not has_saved and not has_planned:
            await update.message.reply_text(
                "Номер не найден в текущем списке.",
                reply_markup=_journal_reply_markup(context),
            )
            return
        await update.message.reply_text(
            _format_room_action_text(session, room),
            reply_markup=room_action_keyboard(room, has_saved),
        )
        return

    # Ввод списка номеров текстом
    rooms, duplicates = _parse_rooms(text)
    if duplicates:
        await update.message.reply_text(
            f"В списке повторяются номера: {', '.join(duplicates)}. Убери повторы и отправь ещё раз.",
            reply_markup=_journal_reply_markup(context),
        )
        return
    if not rooms:
        await update.message.reply_text(
            "Введи номера комнат: цифры, можно с буквой (512, 12а).",
            reply_markup=_journal_reply_markup(context),
        )
        return

    editing_list = session.get("awaiting_room_list") or session.get("editing_room_list")
    if session.get("editing_room_list"):
        replace_room_list(context, rooms)
    else:
        set_room_list(context, rooms)
        session["work_mode"] = True

    session["awaiting_room_list"] = False
    session["editing_room_list"] = False

    await _update_journal(context)
    msg = "Список номеров обновлён." if editing_list and session.get("pending_rooms") else "Список добавлен."
    await update.message.reply_text(
        f"{msg} Выбери номер кнопкой внизу.",
        reply_markup=_journal_reply_markup(context),
    )


# ─── Итоги ───────────────────────────────────────────────────────────────────

async def _send_totals(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    target_date: date,
    label: str,
) -> None:
    totals = get_daily_totals(target_date)
    session = get_session(context)
    in_work_mode = session.get("work_mode")
    reply_markup = _journal_reply_markup(context) if in_work_mode else home_reply_keyboard()

    if not totals:
        await update.message.reply_text(
            f"📊 {label} ({target_date.strftime('%d.%m.%Y')})\n\nСписаний пока нет.",
            reply_markup=reply_markup,
        )
        return

    lines = [f"📊 {label} ({target_date.strftime('%d.%m.%Y')})\n"]
    for key in DISPLAY_ORDER:
        count = totals.get(key, 0)
        if count > 0:
            lines.append(f"• {ALL_ITEMS[key]}: {count}")
    for key, count in totals.items():
        if key not in ALL_ITEMS and count > 0:
            lines.append(f"• {key}: {count}")
    total_units = sum(totals.values())
    lines.append(f"\n📦 Итого единиц: {total_units}")

    await update.message.reply_text("\n".join(lines), reply_markup=reply_markup)

    html_path = _write_daily_html(target_date, label)
    if html_path:
        await update.message.reply_document(
            document=InputFile(html_path, filename=f"itogi_{target_date.isoformat()}.html"),
            caption=f"{label} — подробный отчёт",
        )


def _write_daily_html(target_date: date, label: str) -> str | None:
    from pathlib import Path
    from bot.config import DATA_DIR
    from bot.html_export import render_full_html

    data = load_history()
    date_str = target_date.isoformat()
    filtered = {
        "batches": [b for b in data.get("batches", []) if b.get("date") == date_str]
    }
    if not filtered["batches"]:
        return None

    content = render_full_html(filtered)
    path = Path(DATA_DIR) / f"itogi_{date_str}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path.resolve())


# ─── Вспомогательные функции ─────────────────────────────────────────────────

def _looks_like_room(text: str) -> bool:
    if not text or len(text) > 6:
        return False
    return bool(re.match(r"^[\dа-яА-Яa-zA-Z\-]+$", text))


def _parse_rooms(text: str) -> tuple[list[str], list[str]]:
    rooms: list[str] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    for token in re.split(r"[\s,;]+", text):
        room = token.strip()
        if not _looks_like_room(room):
            continue
        if room in seen:
            if room not in duplicates:
                duplicates.append(room)
            continue
        rooms.append(room)
        seen.add(room)
    return rooms, duplicates


def _planned_room_index(session: dict, room: str) -> int | None:
    try:
        return session["planned_rooms"].index(room)
    except ValueError:
        return None


def _pending_room_index(session: dict, room: str) -> int | None:
    for index, entry in enumerate(session["pending_rooms"]):
        if entry["room"] == room:
            return index
    return None


def _room_from_button_text(text: str) -> str | None:
    if text.startswith(ROOM_DONE_PREFIX):
        return text[len(ROOM_DONE_PREFIX):].strip()
    if text.startswith(ROOM_PREFIX):
        return text[len(ROOM_PREFIX):].strip()
    return None


def _format_room_action_text(session: dict, room: str) -> str:
    pending_index = _pending_room_index(session, room)
    if pending_index is None:
        return f"🏨 Номер {room}\n\nСписание ещё не записано."
    entry = session["pending_rooms"][pending_index]
    return format_summary(room, entry["counts"], is_editing=True)


# ─── Callback (inline кнопки) ─────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    session = get_session(context)

    if data == CB_MAIN:
        if session["room"]:
            await query.answer("Сначала сохрани текущий номер", show_alert=True)
            return
        await query.edit_message_text("Главное меню. Выбери номер кнопкой внизу.")
        return

    if session["room"] and (
        data == CB_LIST
        or data == CB_SUBMIT
        or data.startswith(CB_ROOM)
        or data.startswith(CB_EDIT)
        or data.startswith(CB_RECORD)
        or data.startswith(CB_EDIT_ROOM)
    ):
        await query.answer("Сначала сохрани текущий номер", show_alert=True)
        return

    if data.startswith(CB_RECORD):
        room = data[len(CB_RECORD):].strip()
        index = _planned_room_index(session, room)
        if index is None or not start_room_from_plan(context, index):
            await query.answer("Номер уже записан или список изменился", show_alert=True)
            await _update_journal(context, via_query=query)
            return
        await _edit_room_panel(query, context)
        return

    if data.startswith(CB_EDIT_ROOM):
        room = data[len(CB_EDIT_ROOM):].strip()
        index = _pending_room_index(session, room)
        if index is None or not start_edit_room(context, index):
            await query.answer("Не получилось открыть номер", show_alert=True)
            await _update_journal(context, via_query=query)
            return
        await _edit_room_panel(query, context)
        return

    if data == CB_LIST:
        session["awaiting_room_list"] = True
        await query.message.reply_text(
            "Отправь список номеров одним сообщением: через пробел, запятую или с новой строки."
        )
        return

    if data == CB_SUBMIT:
        await _submit_batch(query, context)
        return

    if data.startswith(CB_ROOM):
        index = _parse_index(data, CB_ROOM)
        if index is None or not start_room_from_plan(context, index):
            await query.answer("Номер уже выбран или список изменился", show_alert=True)
            await _update_journal(context, via_query=query)
            return
        await _send_room_panel_from_query(query, context)
        return

    if data.startswith(CB_EDIT):
        index = _parse_index(data, CB_EDIT)
        if index is None or not start_edit_room(context, index):
            await query.answer("Не получилось открыть номер", show_alert=True)
            await _update_journal(context, via_query=query)
            return
        await _send_room_panel_from_query(query, context)
        return

    if not session["room"]:
        if data.startswith(CB_ADD) or data in (CB_BACK, CB_UNDO, CB_SAVE, CB_NOTHING) or data.startswith(CB_MENU):
            await query.answer("Сначала выбери номер", show_alert=True)
        return

    if data == CB_BACK:
        session["submenu"] = None
        await _edit_room_panel(query, context)
        return

    if data == CB_UNDO:
        room = session["room"]
        reset_current_room(context)
        await query.edit_message_text(f"↩ Номер {room} отменён.")
        await query.message.reply_text(
            "Выбери номер кнопкой внизу.",
            reply_markup=_journal_reply_markup(context),
        )
        return

    if data == CB_SAVE:
        await _save_current_room(query, context)
        return

    if data == CB_NOTHING:
        session["counts"] = {}
        session["history"] = []
        await _save_current_room(query, context, allow_empty=True)
        return

    if data.startswith(CB_MENU):
        session["submenu"] = data[len(CB_MENU):]
        await _edit_room_panel(query, context)
        return

    if data.startswith(CB_ADD):
        key = data[len(CB_ADD):]
        if key not in ALL_ITEMS:
            return
        if not _can_add(session["counts"], key):
            await query.answer("Достигнут лимит для этой категории", show_alert=True)
            return
        session["counts"][key] = session["counts"].get(key, 0) + 1
        push_history(context, key)
        await _edit_room_panel(query, context)
        return


def _parse_index(data: str, prefix: str) -> int | None:
    try:
        return int(data[len(prefix):])
    except ValueError:
        return None


def _can_add(counts: dict[str, int], key: str) -> bool:
    if key in TEA_KEYS:
        return category_total(counts, TEA_KEYS) < (category_limit(TEA_KEYS) or 2)
    if key in COFFEE_KEYS:
        return category_total(counts, COFFEE_KEYS) < (category_limit(COFFEE_KEYS) or 3)
    return True


async def _save_current_room(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    allow_empty: bool = False,
) -> None:
    session = get_session(context)
    room = session["room"]
    counts = session["counts"]
    is_editing = session.get("editing_index") is not None

    if not counts and not allow_empty:
        await query.answer("Выбери позиции или нажми «Ничего»", show_alert=True)
        return

    add_pending_room(context, room, counts)
    reset_current_room(context)
    await _update_journal(context)

    action = "обновлён" if is_editing else "сохранён"
    await query.edit_message_text(f"✅ Номер {room} {action}.")
    await query.message.reply_text(
        "Выбери следующий номер кнопкой внизу.",
        reply_markup=_journal_reply_markup(context),
    )


async def _submit_batch(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = get_session(context)
    pending = session["pending_rooms"]

    if not pending:
        await query.answer("Нет сохранённых номеров", show_alert=True)
        return

    user = query.from_user
    user_id = user.id if user else None
    user_name = (user.full_name or user.username) if user else None

    append_batch(pending, user_id=user_id, user_name=user_name)
    history = load_history()
    html_path = write_html_export(history)
    text_path = write_text_export(history)
    confirmation = format_submit_confirmation(pending)

    await query.message.reply_text(confirmation)
    await query.message.reply_document(
        document=InputFile(html_path, filename="spisaniya.html"),
        caption="Все списания (HTML)",
    )
    await query.message.reply_document(
        document=InputFile(text_path, filename="spisaniya.txt"),
        caption="Все списания (TXT)",
    )

    clear_pending(context)
    reset_current_room(context)
    session["work_mode"] = False

    # Возврат в главное меню
    await query.message.reply_text(WELCOME_TEXT, reply_markup=home_reply_keyboard())


async def _submit_batch_from_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    session = get_session(context)
    pending = session["pending_rooms"]

    if not pending:
        await update.message.reply_text(
            "Нет сохранённых номеров.",
            reply_markup=_journal_reply_markup(context),
        )
        return

    user = update.effective_user
    user_id = user.id if user else None
    user_name = (user.full_name or user.username) if user else None

    append_batch(pending, user_id=user_id, user_name=user_name)
    history = load_history()
    html_path = write_html_export(history)
    text_path = write_text_export(history)
    confirmation = format_submit_confirmation(pending)

    await update.message.reply_text(confirmation)
    await update.message.reply_document(
        document=InputFile(html_path, filename="spisaniya.html"),
        caption="Все списания (HTML)",
    )
    await update.message.reply_document(
        document=InputFile(text_path, filename="spisaniya.txt"),
        caption="Все списания (TXT)",
    )

    clear_pending(context)
    reset_current_room(context)
    session["work_mode"] = False

    # Возврат в главное меню
    await update.message.reply_text(WELCOME_TEXT, reply_markup=home_reply_keyboard())


async def _update_journal(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    via_query=None,
) -> None:
    session = get_session(context)
    text = format_journal(session["pending_rooms"], session["planned_rooms"])
    chat_id = session.get("journal_chat_id")
    message_id = session.get("journal_message_id")

    if not chat_id or not message_id:
        return

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
        )
    except Exception:
        if via_query:
            msg = await via_query.message.reply_text(text)
            set_journal_message(context, msg.chat_id, msg.message_id)


async def _send_room_panel_from_query(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = get_session(context)
    text = format_summary(
        session["room"],
        session["counts"],
        is_editing=session.get("editing_index") is not None,
    )
    msg = await query.message.reply_text(text, reply_markup=_keyboard_for(session))
    session["panel_message_id"] = msg.message_id


async def _edit_room_panel(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = get_session(context)
    text = format_summary(
        session["room"],
        session["counts"],
        is_editing=session.get("editing_index") is not None,
    )
    await query.edit_message_text(text, reply_markup=_keyboard_for(session))


def _keyboard_for(session):
    if session.get("submenu"):
        return submenu_keyboard(session["submenu"], session["counts"])
    return main_keyboard(session["counts"])


def _journal_reply_markup(context):
    session = get_session(context)
    return journal_reply_keyboard(session["pending_rooms"], session["planned_rooms"])
