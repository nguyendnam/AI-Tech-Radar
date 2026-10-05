"""Read-only connection checks; does not send Telegram messages or write rows."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import requests

from src.ai import get_client
from src.config import GEMINI_MODEL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.database import TABLE
from src.database import get_client as get_database


def main():
    response = get_client().models.generate_content(
        model=GEMINI_MODEL,
        contents="Say OK",
        config={"automatic_function_calling": {"disable": True}},
    )
    if not response.text:
        raise RuntimeError("Gemini returned empty text")
    print("Gemini OK")
    get_database().table(TABLE).select("id").limit(1).execute()
    print("Supabase OK")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Missing Telegram config")
    response = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChat",
        params={"chat_id": TELEGRAM_CHAT_ID},
        timeout=30,
    )
    if response.status_code != 200 or not response.json().get("ok"):
        raise RuntimeError("Telegram connection failed")
    print("Telegram OK")


if __name__ == "__main__":
    main()
