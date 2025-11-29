from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)

# Telegram Bot bilgileri
TELEGRAM_BOT_TOKEN = "7103969863:AAHb8eDRKHmCsevIl2yYtu67AcrBuLaSPvo"
TELEGRAM_CHAT_ID = "-4759460082"

def format_ticker_for_mexc(ticker):
    """
    TradingView ticker formatını MEXC formatına çevirir
    Örnek: BINANCE:XLMUSDT -> XLM_USDT
    """
    # Exchange prefix'ini kaldır (BINANCE:, MEXC:, vb.)
    ticker = ticker.split(':')[-1]
    
    # USDT'yi ayır
    if 'USDT' in ticker:
        base = ticker.replace('USDT', '')
        return f"{base}_USDT"
    elif 'BUSD' in ticker:
        base = ticker.replace('BUSD', '')
        return f"{base}_BUSD"
    else:
        # Diğer pair'ler için genel format
        return ticker

@app.route('/')
def home():
    return "TradingView Webhook Service is running! 🚀"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # TradingView'dan gelen veriyi al
        data = request.json
        
        # Gerekli alanları çıkar
        ticker = data.get('ticker', 'N/A')
        close = data.get('close', 'N/A')
        interval = data.get('interval', 'N/A')
        
        # MEXC için ticker formatını düzenle
        mexc_ticker = format_ticker_for_mexc(ticker)
        
        # Telegram mesajını oluştur
        message = f"""*{ticker}*: ⚠️ WARNING: 1H!
Momentum yükseldi - işlem girişi kontrol et!

💰 Fiyat: {close}
⏰ Period: {interval}

📊 [TradingView'da Aç](https://www.tradingview.com/chart/?symbol={ticker})
💹 [MEXC Futures'da Aç](https://www.mexc.com/en-TR/futures/{mexc_ticker})"""
        
        # Telegram'a gönder
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        response = requests.post(telegram_url, json=payload)
        
        if response.status_code == 200:
            return jsonify({"status": "success", "message": "Telegram'a gönderildi!"}), 200
        else:
            return jsonify({"status": "error", "message": response.text}), 500
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)