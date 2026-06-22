from flask import Flask, request, jsonify
import requests
import os
import json

app = Flask(__name__)

# ============================================================
#   KONFIGURASI — isi via Environment Variables di Railway
# ============================================================
TELEGRAM_TOKEN    = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID  = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY")

# ============================================================
#   FUNGSI: Minta analisa ke Groq AI
# ============================================================
def get_ai_reason(signal_text):
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        prompt = f"""Kamu adalah analis trading profesional. 
Berikan analisa singkat maksimal 2 kalimat dalam bahasa Indonesia untuk sinyal trading berikut:

{signal_text}

Fokus pada: kenapa area ini penting dan konfirmasi sinyal yang terjadi.
Jawab langsung tanpa pembuka seperti "Tentu" atau "Berikut analisa".
"""

        body = {
            "model": "llama-3.3-70b-versatile",
            "max_tokens": 150,
            "messages": [
                {"role": "user", "content": prompt}
            ]
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


# ============================================================
#   FUNGSI: Kirim pesan ke Telegram
# ============================================================
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


# ============================================================
#   ENDPOINT: Terima webhook dari TradingView
# ============================================================
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        raw = request.get_data(as_text=True)
        print(f"Received: {raw}")

        try:
            data = json.loads(raw)
        except:
            data = {"text": raw}

        signal_text = data.get("text", raw)

        # Minta analisa AI dari Groq
        ai_reason = get_ai_reason(signal_text)

        # Susun pesan akhir — hapus REASON lama, ganti dengan AI
        lines = signal_text.strip().split("\n")
        message_lines = []
        for line in lines:
            if line.startswith("REASON"):
                continue
            message_lines.append(line)

        message_lines.append(f"REASON : {ai_reason}")
        final_message = "\n".join(message_lines)

        send_telegram(final_message)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================
#   ENDPOINT: Health check
# ============================================================
@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "Bot is running!"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
