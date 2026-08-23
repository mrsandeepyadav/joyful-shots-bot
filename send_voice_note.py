"""
Daily VOICE NOTE sender for the Diamond client group.
Converts today's Joyful Shots text message into audio using ElevenLabs,
then sends it as a Telegram voice note.
"""

import os
import json
import requests
from datetime import date

# ---- CONFIG ----
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "PUT_YOUR_GROUP_CHAT_ID_HERE")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "PUT_YOUR_ELEVENLABS_KEY_HERE")
VOICE_ID = "dxhwlBCxCrnzRlP4wDeE"  # your chosen ElevenLabs voice
MESSAGES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "messages.json")
AUDIO_FILE = "todays_message.mp3"
# -----------------


def load_messages():
    with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def pick_todays_message(messages):
    day_index = date.today().timetuple().tm_yday % len(messages)
    return messages[day_index]


def clean_text_for_speech(text):
    # Remove emojis and markdown-style symbols so the voice reads smoothly
    import re
    text = re.sub(r'[*_#]', '', text)
    text = re.sub(
        r'[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]',
        '', text
    )
    return text.strip()


def generate_audio(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
    }
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    with open(AUDIO_FILE, "wb") as f:
        f.write(response.content)


def send_voice_note():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVoice"
    with open(AUDIO_FILE, "rb") as f:
        files = {"voice": f}
        data = {"chat_id": TELEGRAM_CHAT_ID}
        response = requests.post(url, data=data, files=files, timeout=30)
    response.raise_for_status()
    return response.json()


def main():
    if "PUT_YOUR" in TELEGRAM_BOT_TOKEN or "PUT_YOUR" in TELEGRAM_CHAT_ID or "PUT_YOUR" in ELEVENLABS_API_KEY:
        raise SystemExit(
            "Please set TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, and ELEVENLABS_API_KEY "
            "as environment variables (or edit this file directly)."
        )

    messages = load_messages()
    todays_text = clean_text_for_speech(pick_todays_message(messages))
    generate_audio(todays_text)
    result = send_voice_note()
    print("Voice note sent:", result.get("ok"))


if __name__ == "__main__":
    main()
