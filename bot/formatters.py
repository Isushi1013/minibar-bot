from bot.catalog import ALL_ITEMS, DISPLAY_ORDER


def _items_lines(counts: dict[str, int]) -> list[str]:
    lines: list[str] = []
    for key in DISPLAY_ORDER:
        n = counts.get(key, 0)
        if n > 0:
            lines.append(f"• {ALL_ITEMS[key]}: {n}")
    return lines


def format_summary(room: str, counts: dict[str, int], *, is_editing: bool = False) -> str:
    title = f"✏️ Изменение номера {room}" if is_editing else f"📋 Номер {room}"
    lines = [title, ""]
    item_lines = _items_lines(counts)
    if item_lines:
        lines.extend(item_lines)
    else:
        lines.append("_Ничего не выбрано. Нажмите кнопки ниже._")
    return "\n".join(lines)


def format_room_block(room: str, counts: dict[str, int]) -> str:
    lines = [f"🏨 Номер {room}"]
    item_lines = _items_lines(counts)
    if item_lines:
        lines.extend(item_lines)
    else:
        lines.append("• Ничего")
    return "\n".join(lines)


def format_journal(pending_rooms: list[dict], planned_rooms: list[str] | None = None) -> str:
    planned_rooms = planned_rooms or []
    if not pending_rooms and not planned_rooms:
        return (
            "📒 Списание смены\n\n"
            "_Пока нет номеров._\n"
            "Нажми «Ввести список номеров» или отправь номер комнаты сообщением."
        )
    lines = ["📒 Списание смены", ""]
    if planned_rooms:
        lines.append("Нужно пройти:")
        lines.append(", ".join(planned_rooms))
        lines.append("")
    if pending_rooms:
        lines.append("Сохранено:")
    for entry in pending_rooms:
        lines.append(format_room_block(entry["room"], entry["counts"]))
        lines.append("")
    lines.append(f"Сохранено номеров: {len(pending_rooms)}")
    if planned_rooms:
        lines.append(f"Осталось: {len(planned_rooms)}")
    return "\n".join(lines).strip()


def format_submit_confirmation(pending_rooms: list[dict]) -> str:
    lines = ["✅ Списание оформлено", ""]
    for entry in pending_rooms:
        lines.append(format_room_block(entry["room"], entry["counts"]))
        lines.append("")
    lines.append(f"Номеров: {len(pending_rooms)}")
    lines.append("Файл data/spisaniya.html обновлён.")
    return "\n".join(lines).strip()
