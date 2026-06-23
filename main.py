from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

TELEGRAM_TOKEN    = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID  = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY")

# Pip size per pair untuk hitung SL buffer 20 pips
PIP_SIZE = {
    "XAUUSD": 0.1,
    "BTCUSD": 1.0,
    "USDJPY": 0.01,
    "GBPUSD": 0.0001,
    "EURUSD": 0.0001,
    "AUDUSD": 0.0001,
    "NZDUSD": 0.0001,
    "USDCAD": 0.0001,
    "USDCHF": 0.0001,
}

def get_pip(pair):
    return PIP_SIZE.get(pair.upper(), 0.0001)

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

Panduan:
- STRONG BUY/SELL : konfirmasi momentum candle + area supply demand
- BUY/SELL        : sinyal dari area supply demand zone
- BUY ZONE/SELL ZONE : sinyal dari momentum candle murni

Jawab langsung tanpa pembuka.
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
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Analisa tidak tersedia ({str(e)})"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def parse_pipe(raw):
    """Parse format: KEY:VALUE|KEY:VALUE"""
    data = {}
    for part in raw.strip().split("|"):
        if ":" in part:
            k, _, v = part.partition(":")
            data[k.strip().upper()] = v.strip()
    return data

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        raw = request.get_data(as_text=True).strip()
        print(f"Received: {raw}")

        data   = parse_pipe(raw)
        signal = data.get("SIGNAL", "UNKNOWN")
        pair   = data.get("PAIR",   "UNKNOWN")
        tf     = data.get("TF",     "?")
        entry  = data.get("ENTRY",  "?")
        high   = data.get("HIGH",   None)
        low    = data.get("LOW",    None)
        tp     = data.get("TP",     None)
        sl     = data.get("SL",     None)
        dtype  = data.get("TYPE",   "SD")

        pip = get_pip(pair)

        # Hitung TP/SL jika belum ada
        try:
            entry_f = float(entry)

            if dtype == "MC" and high and low:
                # BUY ZONE: TP = High, SL = Low - 20 pips
                # SELL ZONE: TP = Low, SL = High + 20 pips
                high_f = float(high)
                low_f  = float(low)
                if "BUY" in signal:
                    tp = f"{high_f:.2f}"
                    sl = f"{low_f - (pip * 20):.2f}"
                else:
                    tp = f"{low_f:.2f}"
                    sl = f"{high_f + (pip * 20):.2f}"

            elif not tp or not sl:
                # Default RR 1:2 jika tidak ada data
                if "BUY" in signal:
                    sl = f"{entry_f - (pip * 20):.2f}"
                    tp = f"{entry_f + (pip * 40):.2f}"
                else:
                    sl = f"{entry_f + (pip * 20):.2f}"
                    tp = f"{entry_f - (pip * 40):.2f}"

        except:
            tp = tp or "-"
            sl = sl or "-"

        # Minta analisa AI
        ai_reason = get_ai_reason(signal, pair, tf, entry, tp, sl)

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
        return {"status": "ok"}, 200

    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "message": str(e)}, 500

@app.route("/", methods=["GET"])
def index():
    return {"status": "Bot is running!"}, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
