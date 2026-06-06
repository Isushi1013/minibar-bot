import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
HISTORY_PATH = str(DATA_DIR / "history.json")
HTML_EXPORT_PATH = str(DATA_DIR / "spisaniya.html")
TXT_EXPORT_PATH = str(DATA_DIR / "spisaniya.txt")


def get_token() -> str:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Задай BOT_TOKEN в файле .env")
    return token
