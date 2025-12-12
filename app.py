from flask import Flask, request, jsonify
import requests
import re
import os

app = Flask(__name__)

# Telegram Bot bilgileri (Environment variable'dan al)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = "-4759460082"

def format_ticker_for_mexc(ticker):
    """
    TradingView ticker formatını MEXC formatına çevirir
    Örnek: BINANCE:XLMUSDT -> XLM_USDT
    Örnek: XLM.P -> XLM
    """
    # Exchange prefix'ini kaldır (BINANCE:, MEXC:, vb.)
    ticker = ticker.split(':')[-1]
    
    # .P, .PS gibi ekleri temizle
    ticker = ticker.replace('.P', '').replace('.PS', '')
    
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
        # TradingView'dan gelen veriyi al (Content-Type'a bakmadan)
        if request.is_json:
            data = request.json
        else:
            # Eğer JSON değilse, text olarak al ve parse et
            import json
            data = json.loads(request.data.decode('utf-8'))
        
        print(f"Received data: {data}")  # Debug log
        
        # Gerekli alanları çıkar
        ticker = data.get('ticker', 'N/A')
        close = data.get('close', 'N/A')
        open_price = data.get('open', 'N/A')
        high = data.get('high', 'N/A')
        low = data.get('low', 'N/A')
        volume = data.get('volume', 'N/A')
        change = data.get('change', 'N/A')
        change_percentage = data.get('change_percentage', 'N/A')
        interval = data.get('interval', 'N/A')
        
        # MEXC için ticker formatını düzenle
        mexc_ticker = format_ticker_for_mexc(ticker)
        
        # Değişim için emoji seç
        try:
            change_value = float(str(change).replace('+','').replace('%',''))
            change_emoji = "📈" if change_value > 0 else "📉"
        except:
            change_emoji = "📊"
        
        # Bar rengi ve yüzde değişim belirle (close vs open)
        try:
            close_value = float(str(close))
            open_value = float(str(open_price))
            bar_change_percent = ((close_value - open_value) / open_value) * 100
            
            if close_value > open_value:
                bar_emoji = "🟢"
                bar_text = f"Yeşil Bar (+{bar_change_percent:.2f}%)"
            elif close_value < open_value:
                bar_emoji = "🔴"
                bar_text = f"Kırmızı Bar ({bar_change_percent:.2f}%)"
            else:
                bar_emoji = "⚪"
                bar_text = "Nötr Bar (0.00%)"
        except:
            bar_emoji = "⚪"
            bar_text = "Bar bilgisi yok"
        
        # Telegram mesajını oluştur
        message = f"""🔔 *{mexc_ticker} Sinyali*

💰 Fiyat: ${close}
{change_emoji} Değişim: {change} ({change_percentage})
{bar_emoji} {bar_text}
📊 Range: ${low} - ${high}
📦 Hacim: {volume}
⏰ {interval}

⚠️ *⬆️ FILTERED CROSSOVER UP! OR ⬇️ FILTERED CROSSOVER DOWN!*

[📊 TradingView](https://www.tradingview.com/chart/?symbol={ticker}) | [💹 MEXC Futures](https://www.mexc.com/en-TR/futures/{mexc_ticker})"""
        
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
            print("Telegram'a başarıyla gönderildi!")  # Debug log
            return jsonify({"status": "success", "message": "Telegram'a gönderildi!"}), 200
        else:
            print(f"Telegram hatası: {response.text}")  # Debug log
            return jsonify({"status": "error", "message": response.text}), 500
            
    except Exception as e:
        print(f"HATA: {str(e)}")  # Debug log
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

