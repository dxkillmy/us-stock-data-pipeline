import os
import requests

def send_discord_alert(message):
    url = os.getenv("DISCORD_WEBHOOK_URL")
    if not url:
        return
    try:
        requests.post(url, json={"content": message[:2000]}, timeout=10)
    except requests.RequestException as e:
        print(f"⚠️ Discord alert error: {type(e).__name__}")