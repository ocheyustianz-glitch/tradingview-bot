from flask import Flask, request, jsonify
import requests
import os
import json

app = Flask(__name__)

TELEGRAM_TOKEN    = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID  = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY")

def get_ai_reason(signal, pair, tf, entry, tp, sl):
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        prompt = f"""Kamu adalah analis trading profesional.
Berikan analisa singkat maksimal 2 kalimat dalam bahasa Indonesia untuk sinyal berikut:
- Sinyal    : {signal}
- Pair      : {pair}
- Timeframe : M{tf}
- Entry     : {entry}
- TP        : {tp}
- SL        : {sl}

Panduan analisa:
- STRONG BUY / STRONG SELL : gabungan konfirmasi momentum candle dan area supply demand
- BUY / SELL               : sinyal dari area supply demand zone
- BUY ZONE / SELL ZONE     : sinyal dari momentum candle murni

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
            headers=headers, json=body, timeout=15
        )
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Analisa tidak tersedia ({str(e)})"


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")


def parse_alert(raw):
    """Parse pesan dari Pine Script (format key : value per baris)"""
    lines = raw.strip().split("\n")
    data  = {}
    for line in lines:
        if ":" in line:
            key, _, val = line.partition(":")
            data[key.strip().upper()] = val.strip()
    return data


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        raw = request.get_data(as_text=True)
        print(f"Received: {raw}")

        data   = parse_alert(raw)
        signal = data.get("SIGNAL", "UNKNOWN")
        pair   = data.get("PAIR",   "UNKNOWN")
        tf     = data.get("TIMEFRAME", "?").replace("M","")
        entry  = data.get("PRICE ENTRY", data.get("ENTRY", "?"))
        tp     = data.get("TP",  "-")
        sl     = data.get("SL",  "-")
        result = data.get("RESULT", "")

        # ── HIT TP ──
        if signal == "HIT TP":
            orig_signal = data.get("SIGNAL ASAL", signal)
            message = (
                "HIT TP!\n"
                f"SIGNAL       : {orig_signal}\n"
                f"PAIR         : {pair}\n"
                f"TIMEFRAME    : {tf}\n"
                f"ENTRY        : {entry}\n"
                f"TP           : {tp}\n"
                f"RESULT       : PROFIT"
            )
            send_telegram(message)
            return jsonify({"status": "ok"}), 200

        # ── HIT SL ──
        if signal == "HIT SL":
            orig_signal = data.get("SIGNAL ASAL", signal)
            message = (
                "HIT SL!\n"
                f"SIGNAL       : {orig_signal}\n"
                f"PAIR         : {pair}\n"
                f"TIMEFRAME    : {tf}\n"
                f"ENTRY        : {entry}\n"
                f"SL           : {sl}\n"
                f"RESULT       : LOSS"
            )
            send_telegram(message)
            return jsonify({"status": "ok"}), 200

        # ── Tambahkan emoji berdasarkan jenis sinyal ──
        emoji = ""
        if "STRONG BUY" in signal:
            emoji = "STRONG BUY"
        elif "STRONG SELL" in signal:
            emoji = "STRONG SELL"
        elif "BUY ZONE" in signal:
            emoji = "BUY ZONE"
        elif "SELL ZONE" in signal:
            emoji = "SELL ZONE"
        elif "BUY" in signal:
            emoji = "BUY"
        elif "SELL" in signal:
            emoji = "SELL"
        else:
            emoji = signal

        # ── Minta analisa AI ──
        ai_reason = get_ai_reason(signal, pair, tf, entry, tp, sl)

        # ── Format pesan Telegram ──
        early_tag = "[EARLY] " if "[EARLY]" in raw else ""
        message = (
            f"{early_tag}"
            f"SIGNAL       : {emoji}\n"
            f"PAIR         : {pair}\n"
            f"TIMEFRAME    : {tf}\n"
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
