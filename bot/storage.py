import json
import os
from threading import Lock
from datetime import datetime, date, timedelta
from pathlib import Path
from collections import defaultdict

from bot.config import HISTORY_PATH

BATCHES_KEY = "batches"
_HISTORY_LOCK = Lock()


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_history() -> dict:
    path = Path(HISTORY_PATH)
    if not path.exists():
        return {BATCHES_KEY: []}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_history(data: dict) -> None:
    path = Path(HISTORY_PATH)
    _ensure_parent(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_batch(rooms: list[dict], user_id: int | None = None, user_name: str | None = None) -> str:
    with _HISTORY_LOCK:
        data = load_history()
        batch_id = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data[BATCHES_KEY].append(
            {
                "id": batch_id,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "date": date.today().isoformat(),
                "user_id": user_id,
                "user_name": user_name,
                "rooms": [
                    {"room": r["room"], "counts": dict(r["counts"])}
                    for r in rooms
                ],
            }
        )
        save_history(data)
        return batch_id


def get_daily_totals(target_date: date | None = None) -> dict[str, int]:
    """Суммирует списания всех пользователей за указанный день."""
    if target_date is None:
        target_date = date.today()
    date_str = target_date.isoformat()

    data = load_history()
    totals: dict[str, int] = defaultdict(int)

    for batch in data[BATCHES_KEY]:
        if batch.get("date") == date_str:
            for room in batch.get("rooms", []):
                for item, count in room.get("counts", {}).items():
                    totals[item] += count

    return dict(totals)


def reset_daily_data() -> None:
    """Архивирует текущий день — ничего не удаляет, просто метка для логики.
    Данные хранятся бессрочно и фильтруются по полю 'date'."""
    pass  # Данные уже разделены по полю date, сброс не нужен
