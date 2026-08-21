"""
Daily Telegram sender for the Diamond client group.

WHAT THIS DOES
- Reads messages.json (30 daily coaching messages)
- Picks the message for "today" based on the date, cycling every 30 days
- Sends it to your Telegram group via the Bot API

HOW TO RUN IT AUTOMATICALLY EVERY DAY AT 9:30 AM
------------------------------------------------
Option A — cron (Linux/Mac server, e.g. a small VPS):
    1. Fill in BOT_TOKEN and CHAT_ID below (or set them as environment variables).
    2. Run:  crontab -e
    3. Add this line (adjust the paths to where you saved the files):
       30 9 * * * /usr/bin/python3 /path/to/send_daily.py >> /path/to/send_daily.log 2>&1

Option B — free hosting (Render / Railway / PythonAnywhere):
    - Upload messages.json + send_daily.py
    - Set BOT_TOKEN and CHAT_ID as environment variables in the host's dashboard
    - Add a "Cron Job" / "Scheduled Task" set to run once daily at 09:30 (your timezone)
    - Command to run: python3 send_daily.py

Either way, this script itself just sends ONE message and exits —
the daily repetition is handled by cron / the host's scheduler, not by this script.
"""

import os
import json
import requests
from datetime import date

# ---- CONFIG: fill these in, or set as environment variables ----
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "PUT_YOUR_GROUP_CHAT_ID_HERE")
MESSAGES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "messages.json")
# ------------------------------------------------------------------


def load_messages():
    with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def pick_todays_message(messages):
    # Cycles through the messages in messages.json based on day-of-year,
    # so it automatically repeats once you reach the end of the list.
    # Add more days to messages.json any time — the script adapts automatically.
    day_index = date.today().timetuple().tm_yday % len(messages)
    return messages[day_index]


def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    response = requests.post(url, data=payload, timeout=15)
    response.raise_for_status()
    return response.json()


def main():
    if "PUT_YOUR" in BOT_TOKEN or "PUT_YOUR" in CHAT_ID:
        raise SystemExit(
            "Please set your BOT_TOKEN and CHAT_ID (either edit this file directly, "
            "or set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID as environment variables)."
        )

    messages = load_messages()
    todays_message = pick_todays_message(messages)
    result = send_message(todays_message)
    print("Sent successfully:", result.get("ok"))


if __name__ == "__main__":
    main()
