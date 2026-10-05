import os

import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")
if not token:
    raise RuntimeError("Hãy điền TELEGRAM_BOT_TOKEN vào .env trước.")

resp = requests.get(
    f"https://api.telegram.org/bot{token}/getUpdates",
    timeout=30,
)
resp.raise_for_status()
data = resp.json()

if not data.get("result"):
    print("Chưa thấy message nào.")
    print("Hãy mở bot Telegram, nhấn Start hoặc gửi 'hello', rồi chạy lại script.")
else:
    seen = set()
    for update in data["result"]:
        msg = update.get("message") or update.get("channel_post") or {}
        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None or chat_id in seen:
            continue
        seen.add(chat_id)
        print(
            f"chat_id={chat_id} | "
            f"type={chat.get('type')} | "
            f"name={chat.get('title') or chat.get('username') or chat.get('first_name')}"
        )
