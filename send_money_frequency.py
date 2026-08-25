"""
Daily "Money Frequency" sender for the Diamond client group.
Sends one message per day, starting from today as Day 1, and looping
back to the first message once the list is exhausted.

Unlike the other senders (which use day-of-year), this one anchors to
a fixed START_DATE so today always sends message #1, tomorrow #2, etc.
"""

import os
import json
import requests
from datetime import date

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "PUT_YOUR_GROUP_CHAT_ID_HERE")
MESSAGES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "money_frequency.json")

# The date this series starts -- today's message will be #1 from this date onward.
START_DATE = date(2026, 8, 25)


def load_messages():
    with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def pick_todays_message(messages):
    days_since_start = (date.today() - START_DATE).days
    index = days_since_start % len(messages)
    return messages[index]


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
        raise SystemExit("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID as environment variables.")
    messages = load_messages()
    result = send_message(pick_todays_message(messages))
    print("Sent successfully:", result.get("ok"))


if __name__ == "__main__":
    main()
