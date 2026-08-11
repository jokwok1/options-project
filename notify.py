import json
import os
import sys
import urllib.parse
import urllib.request


def send_telegram(token, chat_id, message):
    """Send a message to a Telegram chat via the Bot API. Returns the API response."""

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
    }).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    message_file = sys.argv[1] if len(sys.argv) > 1 else "daily_message.txt"

    if not token or not chat_id:
        print(
            "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set; skipping",
            file=sys.stderr,
        )
        return 0

    try:
        with open(message_file, encoding="utf-8") as f:
            message = f.read().strip()
    except FileNotFoundError:
        print(f"{message_file} not found; skipping", file=sys.stderr)
        return 0

    if not message:
        print("empty message; skipping", file=sys.stderr)
        return 0

    result = send_telegram(token, chat_id, message)
    if result.get("ok"):
        print("message sent")
        return 0
    print(f"telegram error: {result}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
