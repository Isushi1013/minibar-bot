from typing import Any


def get_session(context) -> dict[str, Any]:
    if "session" not in context.user_data:
        context.user_data["session"] = _empty_session()
    return context.user_data["session"]


def _empty_session() -> dict[str, Any]:
    return {
        "room": None,
        "counts": {},
        "history": [],
        "panel_message_id": None,
        "submenu": None,
        "planned_rooms": [],
        "pending_rooms": [],
        "editing_index": None,
        "journal_message_id": None,
        "journal_chat_id": None,
        "awaiting_room_list": False,
        "editing_room_list": False,
    }


def reset_current_room(context) -> None:
    s = get_session(context)
    s["room"] = None
    s["counts"] = {}
    s["history"] = []
    s["submenu"] = None
    s["panel_message_id"] = None
    s["editing_index"] = None


def reset_session(context) -> None:
    context.user_data["session"] = _empty_session()


def clear_pending(context) -> None:
    s = get_session(context)
    s["pending_rooms"] = []
    s["planned_rooms"] = []
    s["awaiting_room_list"] = False
    s["editing_room_list"] = False


def set_room(context, room: str) -> None:
    s = get_session(context)
    s["room"] = room.strip()
    s["counts"] = {}
    s["history"] = []
    s["submenu"] = None
    s["editing_index"] = None


def set_room_list(context, rooms: list[str]) -> None:
    s = get_session(context)
    existing = set(s["planned_rooms"])
    existing.update(entry["room"] for entry in s["pending_rooms"])
    for room in rooms:
        if room not in existing:
            s["planned_rooms"].append(room)
            existing.add(room)
    s["awaiting_room_list"] = False
    s["editing_room_list"] = False


def replace_room_list(context, rooms: list[str]) -> None:
    s = get_session(context)
    saved_by_room = {entry["room"]: entry for entry in s["pending_rooms"]}
    s["pending_rooms"] = [
        {"room": room, "counts": dict(saved_by_room[room]["counts"])}
        for room in rooms
        if room in saved_by_room
    ]
    saved_rooms = {entry["room"] for entry in s["pending_rooms"]}
    s["planned_rooms"] = [room for room in rooms if room not in saved_rooms]
    s["awaiting_room_list"] = False
    s["editing_room_list"] = False


def start_room_from_plan(context, index: int) -> bool:
    s = get_session(context)
    if index < 0 or index >= len(s["planned_rooms"]):
        return False
    set_room(context, s["planned_rooms"][index])
    return True


def start_edit_room(context, index: int) -> bool:
    s = get_session(context)
    if index < 0 or index >= len(s["pending_rooms"]):
        return False
    entry = s["pending_rooms"][index]
    s["room"] = entry["room"]
    s["counts"] = dict(entry["counts"])
    s["history"] = [
        key
        for key, count in s["counts"].items()
        for _ in range(count)
    ]
    s["submenu"] = None
    s["editing_index"] = index
    return True


def add_pending_room(context, room: str, counts: dict[str, int]) -> None:
    s = get_session(context)
    entry = {"room": room, "counts": dict(counts)}
    editing_index = s.get("editing_index")
    if editing_index is not None and 0 <= editing_index < len(s["pending_rooms"]):
        s["pending_rooms"][editing_index] = entry
        return
    s["pending_rooms"].append(entry)
    if room in s["planned_rooms"]:
        s["planned_rooms"].remove(room)


def set_journal_message(context, chat_id: int, message_id: int) -> None:
    s = get_session(context)
    s["journal_chat_id"] = chat_id
    s["journal_message_id"] = message_id


def push_history(context, key: str) -> None:
    get_session(context)["history"].append(key)


def undo_last(context) -> bool:
    s = get_session(context)
    if not s["history"]:
        return False
    key = s["history"].pop()
    counts = s["counts"]
    if counts.get(key, 0) > 0:
        counts[key] -= 1
        if counts[key] == 0:
            del counts[key]
    return True
