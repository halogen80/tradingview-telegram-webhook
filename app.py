from flask import Flask, request, jsonify
import requests
import os
import json

app = Flask(__name__)

# Telegram Bot bilgileri (Environment variable'dan veya direkt string olarak)
# Not: Test ederken os.environ yerine direkt token'ı yazman gerekebilir.
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = "-4759460082"

def format_ticker_for_mexc(ticker):
    """
    TradingView ticker formatını MEXC formatına çevirir
    """
    # Exchange prefix'ini kaldır
    ticker = ticker.split(':')[-1]
    
    # .P, .PS gibi vadeli işlem ekleri temizle
    ticker = ticker.replace('.P', '').replace('.PS', '')
    
    # USDT/BUSD ayrıştırma
    if 'USDT' in ticker:
        base = ticker.replace('USDT', '')
        return f"{base}_USDT"
    elif 'BUSD' in ticker:
        base = ticker.replace('BUSD', '')
        return f"{base}_BUSD"
    elif 'USD' in ticker:
        base = ticker.replace('USD', '')
        return f"{base}_USDT"
    else:
        return ticker

@app.route('/')
def home():
    return "TradingView PMom+MSS Webhook Service is running! 🚀"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Veriyi al (JSON veya Text)
        if request.is_json:
            data = request.json
        else:
            data = json.loads(request.data.decode('utf-8'))
        
        # 1. TEMEL VERİLERİ AL
        ticker = data.get('ticker', 'N/A')
        close = data.get('close', 'N/A')
        high = data.get('high', 'N/A')
        low = data.get('low', 'N/A')
        volume = data.get('volume', 'N/A')
        interval = data.get('interval', 'N/A')
        
        # 2. ÖZEL İNDİKATÖR VERİLERİNİ AL
        signal_type = data.get('signal_type', 'GENERIC') # MSS, MOMENTUM veya GENERIC
        direction = data.get('direction', 'NEUTRAL')     # BULLISH, BEARISH, BUY, SELL
        stop_loss = data.get('stop_loss', 'N/A')

        # MEXC Ticker Formatı
        mexc_ticker = format_ticker_for_mexc(ticker)

        # 3. MESAJ BAŞLIĞI VE GÖVDE OLUŞTURMA
        header = ""
        body = ""
        emoji = "🔔"

        if signal_type == "MSS":
            # --- MARKET STRUCTURE SHIFT ---
            if "BULLISH" in direction:
                header = "🚨 MARKET STRUCTURE SHIFT (MS+)"
                emoji = "🐂" # Boğa
                body = "Yükseliş Kırılımı (Breakout) gerçekleşti!\nMarket yapısı BOĞA (Bullish) yönüne döndü."
            else:
                header = "🚨 MARKET STRUCTURE SHIFT (MS-)"
                emoji = "🐻" # Ayı
                body = "Düşüş Kırılımı (Breakdown) gerçekleşti!\nMarket yapısı AYI (Bearish) yönüne döndü."
        
        elif signal_type == "MOMENTUM":
            # --- MOMENTUM BUY/SELL ---
            if "BUY" in direction:
                header = "🚀 MOMENTUM BUY SIGNAL"
                emoji = "🟢"
                body = "Momentum pozitife döndü. Alım fırsatı."
            else:
                header = "🔻 MOMENTUM SELL SIGNAL"
                emoji = "🔴"
                body = "Momentum negatife döndü. Satış baskısı."
        
        else:
            # --- GENEL / STANDART SİNYAL ---
            header = f"⚠️ {ticker} UYARISI"
            body = "Momentum veya Fiyat hareketi tespit edildi."

        # 4. TEKNİK DETAYLAR (Bar Rengi vb.)
        try:
            bar_text = ""
            open_price = data.get('open', 0)
            if open_price != 0 and open_price != 'N/A':
                c_val = float(str(close))
                o_val = float(str(open_price))
                change_pct = ((c_val - o_val) / o_val) * 100
                bar_icon = "🟢" if c_val >= o_val else "🔴"
                bar_text = f"\n{bar_icon} Mum Değişimi: %{change_pct:.2f}"
        except:
            bar_text = ""

        stop_text = f"\n🛑 **Stop Loss:** `{stop_loss}`" if stop_loss != 'N/A' else ""

        # 5. FINAL MESAJ
        message = f"""{emoji} *{ticker}* - {interval}

*{header}*

📝 {body}
{stop_text}
{bar_text}

💰 *Fiyat:* `{close}`
📊 *Range:* {low} - {high}
📦 *Hacim:* {volume}

[📊 TradingView](https://www.tradingview.com/chart/?symbol={ticker}) | [💹 MEXC Futures](https://www.mexc.com/en-TR/futures/{mexc_ticker})"""

        # Telegram'a Gönder
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
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
