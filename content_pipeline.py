"""
Content Pipeline: Draft -> AI Polish -> Your Approval -> Auto-added to messages.json

HOW IT WORKS
------------
1. You message your bot PRIVATELY (open a 1-on-1 chat with your bot, search
   its username, and just send it a raw idea/draft).
2. This script (run every few minutes by GitHub Actions) checks for new
   messages from you.
3. New drafts get sent to Claude to polish into the Joyful Shots format.
4. The bot replies to you privately with the polished version, and asks
   you to reply OK to approve, or SKIP to discard.
5. When you reply OK to a pending polished draft, it gets appended to
   messages.json in this same repo automatically -- joining the rotation
   sent daily to your Diamond group.

STATE
-----
Since GitHub Actions runs fresh each time (no memory between runs), this
script keeps track of:
  - last_update_id.json   -> which Telegram messages have already been seen
  - pending_approval.json -> the most recent polished draft awaiting your OK

Both files live in this repo and get committed back automatically.
"""

import os
import json
import requests

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
YOUR_CHAT_ID = os.environ.get("YOUR_PERSONAL_CHAT_ID", "")  # YOUR private chat with the bot, not the group
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

STATE_DIR = os.path.dirname(os.path.abspath(__file__))
LAST_UPDATE_FILE = os.path.join(STATE_DIR, "last_update_id.json")
PENDING_FILE = os.path.join(STATE_DIR, "pending_approval.json")
MESSAGES_FILE = os.path.join(STATE_DIR, "messages.json")

TEMPLATE_INSTRUCTIONS = """You are formatting a daily coaching message for a Telegram group called "Joyful Shots".
Take the user's raw draft idea below and turn it into this exact structure:

Joyful Shots for the Day. [one relevant emoji]

[Short title as a punchy one-line insight, with an emoji]

[1-2 sentence core insight, in simple, everyday language, no jargon]

[A short, relatable daily-life example illustrating the insight -- something an ordinary person would recognize, 2-4 sentences, with one or two emojis]

Question: [a reflective question addressed to "you", tied to the insight] [emoji]

We Luv u. Joyful Team. [emoji]

Keep the language simple enough for someone who didn't finish school easily to understand.
Do not add any preamble, explanation, or notes -- output ONLY the formatted message, nothing else.

Raw draft from the user:
"""


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_new_messages(last_update_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": last_update_id + 1, "timeout": 5}
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    return response.json().get("result", [])


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": YOUR_CHAT_ID, "text": text}, timeout=15)


def polish_with_claude(raw_draft):
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 500,
        "messages": [{"role": "user", "content": TEMPLATE_INSTRUCTIONS + raw_draft}],
    }
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data["content"][0]["text"].strip()


def main():
    if not BOT_TOKEN or not YOUR_CHAT_ID or not ANTHROPIC_API_KEY:
        raise SystemExit("Missing one of: TELEGRAM_BOT_TOKEN, YOUR_PERSONAL_CHAT_ID, ANTHROPIC_API_KEY")

    state = load_json(LAST_UPDATE_FILE, {"last_update_id": 0})
    pending = load_json(PENDING_FILE, {"polished_text": None})

    updates = get_new_messages(state["last_update_id"])

    for update in updates:
        state["last_update_id"] = update["update_id"]
        message = update.get("message", {})
        chat_id = str(message.get("chat", {}).get("id", ""))
        text = message.get("text", "").strip()

        if chat_id != str(YOUR_CHAT_ID) or not text:
            continue

        # Case 1: you're approving a pending draft
        if text.upper() == "OK" and pending.get("polished_text"):
            messages = load_json(MESSAGES_FILE, [])
            messages.append(pending["polished_text"])
            save_json(MESSAGES_FILE, messages)
            send_telegram_message("Added to your Joyful Shots rotation! It'll appear in the daily cycle. 🎉")
            pending = {"polished_text": None}
            continue

        # Case 2: you're discarding a pending draft
        if text.upper() == "SKIP" and pending.get("polished_text"):
            send_telegram_message("Discarded, no problem. Send your next idea whenever you're ready.")
            pending = {"polished_text": None}
            continue

        # Case 3: a brand new raw draft to polish
        polished = polish_with_claude(text)
        pending = {"polished_text": polished}
        send_telegram_message(
            f"Here's the polished version:\n\n{polished}\n\n"
            f"Reply OK to add this to your Joyful Shots rotation, or SKIP to discard it."
        )

    save_json(LAST_UPDATE_FILE, state)
    save_json(PENDING_FILE, pending)


if __name__ == "__main__":
    main()
