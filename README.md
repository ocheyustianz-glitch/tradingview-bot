# TradingView → Claude AI → Telegram Bot

Bot ini menerima alert dari TradingView, menganalisa dengan Claude AI,
lalu mengirim hasilnya ke channel Telegram.

## Alur Kerja
TradingView Alert → Webhook → Bot Python → Claude AI → Telegram

## Deploy ke Railway

1. Upload folder ini ke GitHub
2. Login ke railway.app
3. Klik "New Project" → "Deploy from GitHub repo"
4. Pilih repo ini
5. Tambahkan Environment Variables:

| Variable          | Nilai                        |
|-------------------|------------------------------|
| TELEGRAM_TOKEN    | Token bot dari BotFather     |
| TELEGRAM_CHAT_ID  | -1003702247424               |
| ANTHROPIC_API_KEY | API key dari Anthropic       |

6. Setelah deploy, copy URL dari Railway
7. Webhook URL untuk TradingView: https://URL_RAILWAY/webhook

## Setting Alert TradingView

- Webhook URL: https://URL_RAILWAY/webhook
- Message:
{
  "text": "SIGNAL : STRONG SELL\nPAIR : {{ticker}}\nTIMEFRAME : M{{interval}}\nPRICE ENTRY : {{close}}\nTP : {{plot_0}}\nSL : {{plot_1}}"
}
