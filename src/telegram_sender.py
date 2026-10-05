import time

import requests

from src.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)

# MESSAGE SPLITTER


def _split_message(
    text: str,
    max_len: int = 3500,
) -> list[str]:
    """
    Telegram có giới hạn độ dài message.

    Nếu message quá dài:
    tự động chia thành nhiều message nhỏ.
    """

    if max_len < 2:
        raise ValueError("max_len phải >= 2.")
    if len(text.encode("utf-16-le")) // 2 <= max_len:
        return [text]

    chunks = []

    current = ""

    for paragraph in text.split("\n"):
        candidate = (f"{current}\n{paragraph}").strip()

        if len(candidate.encode("utf-16-le")) // 2 <= max_len:
            current = candidate

        else:
            if current:
                chunks.append(current)

            while len(paragraph.encode("utf-16-le")) // 2 > max_len:
                units = end = 0
                for character in paragraph:
                    size = 2 if ord(character) > 0xFFFF else 1
                    if units + size > max_len:
                        break
                    units += size
                    end += 1
                chunks.append(paragraph[:end])
                paragraph = paragraph[end:]

            current = paragraph

    if current:
        chunks.append(current)

    return chunks


# RETRY


def _send_with_retry(
    endpoint: str,
    payload: dict,
    retries: int = 3,
):
    """
    Gửi Telegram có retry.

    Ví dụ:
    attempt 1 fail
    → chờ
    → attempt 2
    """

    last_error = None

    for attempt in range(
        1,
        retries + 1,
    ):
        try:
            response = requests.post(
                endpoint,
                json=payload,
                timeout=30,
            )
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == retries:
                    raise RuntimeError(f"Telegram failed: HTTP {response.status_code}")
                wait = attempt * 2
                if response.status_code == 429:
                    wait = min(
                        30,
                        max(
                            1,
                            int(
                                response.json()
                                .get("parameters", {})
                                .get("retry_after", wait)
                            ),
                        ),
                    )
                time.sleep(wait)
                continue
            # Never expose the request URL (it contains the bot token) in errors.
            if response.status_code != 200 or not response.json().get("ok"):
                raise RuntimeError(f"Telegram failed: HTTP {response.status_code}")
            return response

        except requests.RequestException as exc:
            last_error = RuntimeError(f"Telegram network failure: {type(exc).__name__}")
            print(f"[WARN] Telegram attempt {attempt}/{retries} failed")

            if attempt < retries:
                wait_time = attempt * 2

                print(f"[INFO] Retry in {wait_time}s...")

                time.sleep(wait_time)

    raise last_error


# PUBLIC FUNCTION


def send_telegram(
    text: str,
):
    """
    Hàm chính để gửi Telegram.
    """

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Thiếu TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID.")

    endpoint = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    messages = _split_message(text)

    for chunk in messages:
        _send_with_retry(
            endpoint,
            {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": chunk,
                "disable_web_page_preview": True,
            },
        )
