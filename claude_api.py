import requests
import threading
import json
import os
API_KEY = os.getenv("OPENROUTER_API_KEY")
# ── Config ─────────────────────────────────────────────────────────────────────
MODELS = [
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "mistralai/mistral-7b-instruct:free",
    "openchat/openchat-7b:free",
]


def _call_api(prompt, max_tokens=150):
    last_error = None
    for model in MODELS:
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://eyeguard.app",
                    "X-Title": "EyeGuard"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens
                },
                timeout=15
            )
            if response.status_code != 200:
                last_error = f"HTTP {response.status_code}"
                print(f"Model {model} failed: {last_error}")
                continue
            data = response.json()
            if "error" in data:
                last_error = data["error"].get("message", str(data["error"]))
                print(f"Model {model} error: {last_error}")
                continue
            text = data["choices"][0]["message"]["content"].strip()
            if text:
                print(f"AI response from: {model}")
                return text
        except requests.exceptions.Timeout:
            last_error = "Timed out"
            print(f"Model {model} timed out")
        except requests.exceptions.ConnectionError:
            last_error = "No internet"
            print(f"Model {model} connection error")
        except Exception as e:
            last_error = str(e)
            print(f"Model {model} error: {e}")
    raise Exception(f"All models failed. Last: {last_error}")


def get_advice(data, callback=None):
    def fetch():
        try:
            mins     = data.get("session_time", 0) // 60
            blink    = data.get("blink_rate", 0)
            distance = data.get("distance_status", "Unknown")
            strain   = data.get("strain_score", 0)

            prompt = f"""You are an eye health expert. Give short practical advice in 2-3 sentences.

Current data:
- Blink rate: {blink} blinks/min (normal: 15-20)
- Screen distance: {distance}
- Eye strain score: {strain}/100
- Session time: {mins} minutes

Be direct and friendly."""

            text = _call_api(prompt, max_tokens=150)
            if callback:
                callback(text)
        except Exception as e:
            msg = f"Could not get advice: {e}"
            print(msg)
            if callback:
                callback(msg)

    threading.Thread(target=fetch, daemon=True).start()


def get_daily_summary(stats, callback=None):
    def fetch():
        try:
            prompt = f"""Eye health daily summary in 3-4 sentences, then 2 tips for tomorrow.



Today:
- Avg blink rate: {stats.get('avg_blink_rate', 0)}/min
- Avg strain: {stats.get('avg_strain', 0)}/100
- Screen time: {stats.get('total_time', 0)} minutes
- Times too close: {stats.get('too_close_count', 0)}"""

            text = _call_api(prompt, max_tokens=200)
            if callback:
                callback(text)
        except Exception as e:
            msg = f"Could not get summary: {e}"
            print(msg)
            if callback:
                callback(msg)

    threading.Thread(target=fetch, daemon=True).start()


def init_client(api_key=None):
    global API_KEY
    if api_key:
        API_KEY = api_key
    print("OpenRouter AI ready!")
    return True
