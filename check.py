import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

URL = "https://clantax.de"
WEBHOOK = os.environ["DISCORD_WEBHOOK"]
STATE_FILE = "state.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (StatusBot)"}


def check():
    """Gibt (online, statuscode, antwortzeit_ms) zurück."""
    start = time.time()
    req = urllib.request.Request(URL, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception:
        return False, None, None
    ms = int((time.time() - start) * 1000)
    return code < 400, code, ms


def discord(method, url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        method=method,
        headers={"Content-Type": "application/json", "User-Agent": "StatusBot"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        body = r.read()
        return json.loads(body) if body else {}


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def main():
    state = load_state()
    online, code, ms = check()
    now = datetime.now(timezone.utc)

    embed = {
        "title": "Status: clantax.de",
        "url": URL,
        "color": 0x2ECC71 if online else 0xE74C3C,
        "description": "🟢 **Online**" if online else "🔴 **Offline**",
        "fields": [
            {"name": "HTTP-Code", "value": str(code or "–"), "inline": True},
            {"name": "Antwortzeit", "value": f"{ms} ms" if ms else "–", "inline": True},
            {"name": "Letzter Check", "value": f"<t:{int(now.timestamp())}:R>", "inline": True},
        ],
        "timestamp": now.isoformat(),
    }
    payload = {"embeds": [embed]}

    msg_id = state.get("message_id")
    if msg_id:
        try:
            discord("PATCH", f"{WEBHOOK}/messages/{msg_id}", payload)
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            msg_id = None  # Nachricht wurde gelöscht -> neu erstellen
    if not msg_id:
        msg_id = discord("POST", WEBHOOK + "?wait=true", payload)["id"]

    new_state = {"message_id": msg_id, "online": online}
    if new_state != state:
        with open(STATE_FILE, "w") as f:
            json.dump(new_state, f)


if __name__ == "__main__":
    main()
