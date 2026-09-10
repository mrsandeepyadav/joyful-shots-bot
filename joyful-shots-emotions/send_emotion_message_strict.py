"""
Strict sender for the 30-day Emotional Pattern series.

Key differences from the earlier version:
  - The SLOT is now passed in explicitly by the workflow (not guessed from
    the clock), so there is zero ambiguity about which message goes out.
  - A guard file (sent_log.json) records exactly which (day, slot) pairs
    have already been sent, so a late/duplicate/manual run can NEVER
    resend the same slot twice.
  - Day 1 always starts on SERIES_START_DATE. If that date is today,
    the very first send will be Day 1 / 08:00 - no ambiguity.

Usage:
    python3 send_emotion_message.py 08:00
    python3 send_emotion_message.py 11:00
    python3 send_emotion_message.py 14:00
    python3 send_emotion_message.py 17:00
    python3 send_emotion_message.py 20:00

Env vars:
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID
    SERIES_START_DATE   e.g. 2026-09-15  (the date Day 1's 08:00 message
                         should go out - set this ONCE and never change it
                         unless you deliberately want to restart the cycle)
"""

import json
import os
import sys
from datetime import date, datetime

import requests

DATA_FILE = os.path.join(os.path.dirname(__file__), "cycle1_emotions.json")

# Log filename is series-specific (set via SERIES_NAME env var) so that
# multiple bot streams (Joyful Shots, Emotional Pattern, Money Frequency,
# etc.) running in the same repo NEVER write to the same log file at the
# same time. Two workflows racing to commit the same file is the actual
# risk here - Telegram itself has no problem with simultaneous sends to
# different chats.
SERIES_NAME = os.environ.get("SERIES_NAME", "emotional_pattern")
LOG_FILE = os.path.join(os.path.dirname(__file__), f"sent_log_{SERIES_NAME}.json")

VALID_SLOTS = ["08:00", "11:00", "14:00", "17:00", "20:00"]


def get_today_day_number(start_date_str: str, total_days: int) -> int:
    start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    today = date.today()
    delta_days = (today - start).days
    if delta_days < 0:
        raise SystemExit(
            f"SERIES_START_DATE ({start_date_str}) is in the future. "
            f"Today is {today}. Fix the start date before running."
        )
    return (delta_days % total_days) + 1


def load_log() -> set:
    if not os.path.exists(LOG_FILE):
        return set()
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return set(tuple(x) for x in json.load(f))


def save_log(log: set) -> None:
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump([list(x) for x in log], f)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in VALID_SLOTS:
        print(f"Usage: python3 send_emotion_message.py <{'|'.join(VALID_SLOTS)}>")
        sys.exit(1)

    slot = sys.argv[1]

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_days = len(data["days"])
    start_date_str = os.environ["SERIES_START_DATE"]
    day_number = get_today_day_number(start_date_str, total_days)
    today_str = date.today().isoformat()

    log = load_log()
    key = (today_str, slot)
    if key in log:
        print(f"Already sent {slot} for {today_str} (Day {day_number}). Skipping - no duplicate.")
        return

    day_entry = next(d for d in data["days"] if d["day"] == day_number)
    message = day_entry["messages"][slot]

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message},
        timeout=15,
    )
    resp.raise_for_status()

    log.add(key)
    save_log(log)

    print(f"Sent Day {day_number} ({day_entry['emotion_pair']}) [{slot}] - {today_str}")


if __name__ == "__main__":
    main()
