from flask import Flask, request, jsonify
import requests
import os
import json

app = Flask(__name__)

# Telegram Bot bilgileri
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = "-4759460082"  # Sabit chat ID

def format_ticker_for_mexc(ticker):
    """
    TradingView ticker formatını MEXC formatına çevirir
    Örnek: BINANCE:XLMUSDT -> XLM_USDT
    """
    ticker = ticker.split(':')[-1]
    ticker = ticker.replace('.P', '').replace('.PS', '')
    
    if 'USDT' in ticker:
        base = ticker.replace('USDT', '')
        return f"{base}_USDT"
    elif 'BUSD' in ticker:
        base = ticker.replace('BUSD', '')
        return f"{base}_BUSD"
    else:
        return ticker

@app.route('/')
def home():
    return "TradingView Webhook Service is running! 🚀"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # TradingView'dan gelen veriyi al
        if request.is_json:
            data = request.json
        else:
            data = json.loads(request.data.decode('utf-8'))
        
        print(f"Received data: {data}")  # Debug log
        
        # --- VERİ AYRIŞTIRMA ---
        action = data.get('action', 'SIGNAL') # BUY, SELL veya SIGNAL
        ticker = data.get('ticker', 'N/A')
        close = data.get('close', 0)
        high = data.get('high', 0)
        low = data.get('low', 0)
        volume = data.get('volume', 0)
        interval = data.get('interval', 'N/A')
        
        # MEXC Ticker Formatı
        mexc_ticker = format_ticker_for_mexc(ticker)
        
        # --- MESAJ TASARIMI (BUY vs SELL) ---
        if action == "BUY":
            header = f"🟢 <b>LONG SİNYALİ GELDİ!</b> 🚀"
            emoji_direction = "⬆️ YÜKSELİŞ BEKLENTİSİ"
            price_emoji = "🟢"
            side_color = "LONG"
        elif action == "SELL":
            header = f"🔴 <b>SHORT SİNYALİ GELDİ!</b> 🩸"
            emoji_direction = "⬇️ DÜŞÜŞ BEKLENTİSİ"
            price_emoji = "🔴"
            side_color = "SHORT"
        else:
            header = f"⚠️ <b>ALARM TETİKLENDİ</b>"
            emoji_direction = "↔️ YÖN BELİRSİZ"
            price_emoji = "⚪"
            side_color = "NÖTR"

        # Telegram Mesaj Şablonu
        message = f"""{header}

🆔 <b>Coin:</b> <code>{mexc_ticker}</code>
⏱️ <b>Zaman:</b> {interval}dk

{price_emoji} <b>Fiyat:</b> ${close}
📊 <b>Yön:</b> {side_color}

🌊 <b>Range:</b> ${low} - ${high}
📦 <b>Hacim:</b> {volume}

{emoji_direction}

🔗 <a href="https://www.tradingview.com/chart/?symbol={ticker}">TradingView</a> | <a href="https://www.mexc.com/en-TR/futures/{mexc_ticker}">MEXC Futures</a>"""
        
        # --- TELEGRAM'A GÖNDERME ---
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML", # HTML modu kullanıyoruz (kalın yazı vs için)
            "disable_web_page_preview": True
        }
        
        response = requests.post(telegram_url, json=payload)
        
        if response.status_code == 200:
            return jsonify({"status": "success", "message": f"{action} signal sent to Telegram!"}), 200
        else:
            print(f"Telegram Error: {response.text}")
            return jsonify({"status": "error", "message": response.text}), 500
            
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
