from flask import Flask, request, jsonify
import requests
import os
import json

app = Flask(__name__)

TELEGRAM_TOKEN    = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID  = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY")

def get_ai_reason(signal, pair, tf, entry):
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        prompt = f"""Kamu adalah analis trading profesional.
Berikan analisa singkat maksimal 2 kalimat dalam bahasa Indonesia untuk sinyal berikut:
- Sinyal  : {signal}
- Pair    : {pair}
- Timeframe: M{tf}
- Entry   : {entry}

Fokus pada: kenapa area ini penting dan konfirmasi sinyal yang terjadi.
Jawab langsung tanpa pembuka seperti "Tentu" atau "Berikut analisa".
"""

        body = {
            "model": "llama-3.3-70b-versatile",
            "max_tokens": 150,
            "messages": [{"role": "user", "content": prompt}]
        }

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=15
        )

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        return f"Analisa tidak tersedia ({str(e)})"


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        raw = request.get_data(as_text=True)
        print(f"Received: {raw}")

        try:
            data = json.loads(raw)
        except:
            data = {}

        # Ambil data dari TradingView
        signal = data.get("signal", "UNKNOWN")
        pair   = data.get("pair",   "UNKNOWN")
        tf     = data.get("tf",     "?")
        entry  = data.get("entry",  "?")
        tp     = data.get("tp",     "-")
        sl     = data.get("sl",     "-")

        # Minta analisa AI
        ai_reason = get_ai_reason(signal, pair, tf, entry)

        # Format pesan Telegram
        message = (
            f"SIGNAL       : {signal}\n"
            f"PAIR         : {pair}\n"
            f"TIMEFRAME    : M{tf}\n"
            f"PRICE ENTRY  : {entry}\n"
            f"TP           : {tp}\n"
            f"SL           : {sl}\n"
            f"REASON : {ai_reason}"
        )

        send_telegram(message)
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "Bot is running!"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
