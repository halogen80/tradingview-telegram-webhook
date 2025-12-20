from flask import Flask, request, jsonify
import requests
import os
import json
from datetime import datetime

app = Flask(__name__)

# Telegram Bot bilgileri
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = "-4759460082"

def format_ticker_for_mexc(ticker):
    """TradingView ticker formatını MEXC formatına çevirir"""
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

def send_telegram_message(message):
    """Telegram'a mesaj gönderir"""
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    response = requests.post(telegram_url, json=payload)
    return response

def format_pcd_geih_signal(data):
    """PCD + GEIH indikatörü için özel mesaj formatı (SADECE ONAYLI SİNYAL)"""
    signal_type = data.get('signal_type', 'UNKNOWN')
    
    # SADECE CONFIRMED sinyallerini işle
    if signal_type != "CONFIRMED":
        return None  # Diğer sinyalleri yoksay
    
    ticker = data.get('ticker', 'N/A')
    mexc_ticker = format_ticker_for_mexc(ticker)
    close = data.get('close', 0)
    interval = data.get('interval', 'N/A')
    
    # PCD durumu
    pcd_state = data.get('pcd_state', 'NORMAL')
    pcd_vol_rank = data.get('pcd_vol_rank', 0)
    
    # GEIH durumu
    geih_value = data.get('geih_value', 0)
    
    # PCD durum emojisi
    pcd_emoji_map = {
        "SQUEEZE": "🔴",
        "PRE_BREAKOUT": "🟠",
        "HIGH_VOL": "🟢",
        "NORMAL": "⚪"
    }
    pcd_emoji = pcd_emoji_map.get(pcd_state, "⚪")
    
    message = f"""✅ <b>STRATEJİK ONAYLI SİNYAL!</b> 🎯

🟠 <b>Coin:</b> <code>{mexc_ticker}</code>
⏱️ <b>Timeframe:</b> {interval}
💰 <b>Fiyat:</b> ${close}

🔥 <b>YÜKSEK ÖNCELİK</b>

📌 <b>DURUM:</b> GEIH Ekstrem + PCD Onaylı

🔷 <b>PCD Analizi:</b>
   {pcd_emoji} Volatilite: {pcd_state}
   📊 Vol Rank: {pcd_vol_rank:.1f}/100

🔶 <b>GEIH Analizi:</b>
   ✅ Ekstrem Hareket: EVET
   📈 Değer: {geih_value:.2f}%

🕐 <b>Zaman:</b> {datetime.now().strftime('%H:%M:%S')}

🔗 <a href="https://www.tradingview.com/chart/?symbol={ticker}">TradingView</a> | <a href="https://www.mexc.com/en-TR/futures/{mexc_ticker}">MEXC Futures</a>"""
    
    return message

def format_standard_signal(data):
    """Standart BUY/SELL sinyalleri için mesaj formatı"""
    action = data.get('action', 'SIGNAL')
    ticker = data.get('ticker', 'N/A')
    mexc_ticker = format_ticker_for_mexc(ticker)
    close = data.get('close', 0)
    high = data.get('high', 0)
    low = data.get('low', 0)
    volume = data.get('volume', 0)
    interval = data.get('interval', 'N/A')
    
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

    message = f"""{header}

🆔 <b>Coin:</b> <code>{mexc_ticker}</code>
⏱️ <b>Zaman:</b> {interval}dk

{price_emoji} <b>Fiyat:</b> ${close}
📊 <b>Yön:</b> {side_color}

🌊 <b>Range:</b> ${low} - ${high}
📦 <b>Hacim:</b> {volume}

{emoji_direction}

🔗 <a href="https://www.tradingview.com/chart/?symbol={ticker}">TradingView</a> | <a href="https://www.mexc.com/en-TR/futures/{mexc_ticker}">MEXC Futures</a>"""
    
    return message

@app.route('/')
def home():
    return """
    <h1>🚀 Multi-Indicator Webhook Service</h1>
    <p>✅ Service is running!</p>
    <h3>Supported Indicators:</h3>
    <ul>
        <li>PCD Squeeze + GEIH v2 Combined</li>
        <li>Standard BUY/SELL Signals</li>
        <li>Custom Indicators</li>
    </ul>
    <h3>Endpoints:</h3>
    <ul>
        <li><code>/webhook</code> - Main webhook (auto-detects indicator type)</li>
        <li><code>/pcd-geih</code> - PCD+GEIH specific endpoint</li>
        <li><code>/standard</code> - Standard signals endpoint</li>
    </ul>
    """

@app.route('/webhook', methods=['POST'])
def webhook():
    """Ana webhook - otomatik indikatör tipini algılar"""
    try:
        # Veri kontrolü ve parse
        raw_data = request.data.decode('utf-8')
        
        # Boş veri kontrolü
        if not raw_data or raw_data.strip() == '':
            print("[WARNING] Empty request body received")
            return jsonify({
                "status": "error", 
                "message": "Empty request body"
            }), 400
        
        # JSON parse
        if request.is_json:
            data = request.json
        else:
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError as e:
                print(f"[JSON ERROR] Invalid JSON: {raw_data[:100]}")
                return jsonify({
                    "status": "error", 
                    "message": f"Invalid JSON format: {str(e)}"
                }), 400
        
        print(f"[WEBHOOK] Received data: {data}")
        
        # İndikatör tipini algıla
        indicator_type = data.get('indicator', 'standard')
        
        if indicator_type == 'pcd_geih' or 'signal_type' in data:
            message = format_pcd_geih_signal(data)
            # Eğer mesaj None ise (CONFIRMED değilse), işlemi atla
            if message is None:
                return jsonify({
                    "status": "filtered", 
                    "message": "Signal ignored (not CONFIRMED)",
                    "signal_type": data.get('signal_type', 'UNKNOWN')
                }), 200
        else:
            message = format_standard_signal(data)
        
        # Telegram'a gönder
        response = send_telegram_message(message)
        
        if response.status_code == 200:
            return jsonify({
                "status": "success", 
                "message": "Signal sent to Telegram!",
                "indicator_type": indicator_type
            }), 200
        else:
            print(f"[ERROR] Telegram Error: {response.text}")
            return jsonify({"status": "error", "message": response.text}), 500
            
    except Exception as e:
        print(f"[CRITICAL ERROR] {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/pcd-geih', methods=['POST'])
def pcd_geih_webhook():
    """PCD + GEIH indikatörü için özel endpoint (SADECE CONFIRMED sinyalleri)"""
    try:
        # Veri kontrolü ve parse
        raw_data = request.data.decode('utf-8')
        
        if not raw_data or raw_data.strip() == '':
            print("[PCD-GEIH WARNING] Empty request body")
            return jsonify({
                "status": "error", 
                "message": "Empty request body"
            }), 400
        
        if request.is_json:
            data = request.json
        else:
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError as e:
                print(f"[PCD-GEIH JSON ERROR] Invalid JSON: {raw_data[:100]}")
                return jsonify({
                    "status": "error", 
                    "message": f"Invalid JSON: {str(e)}"
                }), 400
        
        print(f"[PCD-GEIH] Received data: {data}")
        
        message = format_pcd_geih_signal(data)
        
        # Eğer mesaj None ise (CONFIRMED değilse), işlemi atla
        if message is None:
            print(f"[PCD-GEIH] Signal filtered: {data.get('signal_type', 'UNKNOWN')}")
            return jsonify({
                "status": "filtered", 
                "message": "Signal ignored (not CONFIRMED)",
                "signal_type": data.get('signal_type', 'UNKNOWN')
            }), 200
        
        response = send_telegram_message(message)
        
        if response.status_code == 200:
            return jsonify({
                "status": "success", 
                "message": "CONFIRMED signal sent!",
                "signal_type": "CONFIRMED"
            }), 200
        else:
            return jsonify({"status": "error", "message": response.text}), 500
            
    except Exception as e:
        print(f"[PCD-GEIH ERROR] {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/standard', methods=['POST'])
def standard_webhook():
    """Standart BUY/SELL sinyalleri için endpoint"""
    try:
        # Veri kontrolü ve parse
        raw_data = request.data.decode('utf-8')
        
        if not raw_data or raw_data.strip() == '':
            print("[STANDARD WARNING] Empty request body")
            return jsonify({
                "status": "error", 
                "message": "Empty request body"
            }), 400
        
        if request.is_json:
            data = request.json
        else:
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError as e:
                print(f"[STANDARD JSON ERROR] Invalid JSON: {raw_data[:100]}")
                return jsonify({
                    "status": "error", 
                    "message": f"Invalid JSON: {str(e)}"
                }), 400
        
        print(f"[STANDARD] Received data: {data}")
        
        message = format_standard_signal(data)
        response = send_telegram_message(message)
        
        if response.status_code == 200:
            return jsonify({
                "status": "success", 
                "message": f"{data.get('action', 'SIGNAL')} signal sent!",
            }), 200
        else:
            return jsonify({"status": "error", "message": response.text}), 500
            
    except Exception as e:
        print(f"[STANDARD ERROR] {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/test', methods=['GET'])
def test():
    """Test endpoint - sistem çalışıyor mu kontrol et"""
    test_data = {
        "indicator": "pcd_geih",
        "signal_type": "CONFIRMED",
        "ticker": "BINANCE:BTCUSDT",
        "close": 45230.50,
        "interval": "15",
        "pcd_state": "NORMAL",
        "pcd_vol_rank": 45.5,
        "geih_extreme": True,
        "geih_value": 3.25
    }
    
    message = format_pcd_geih_signal(test_data)
    response = send_telegram_message(message)
    
    if response.status_code == 200:
        return jsonify({
            "status": "success", 
            "message": "Test message sent!",
            "telegram_response": response.json()
        }), 200
    else:
        return jsonify({
            "status": "error", 
            "message": "Test failed",
            "error": response.text
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
