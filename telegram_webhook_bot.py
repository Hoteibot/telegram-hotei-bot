from flask import Flask, request
import requests
import os

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, data=data)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    message = data.get('message', '📈 Сигнал от TradingView!')
    send_telegram_message(f"📢 <b>Сигнал:</b> {message}")
    return 'OK', 200

@app.route('/', methods=['GET'])
def index():
    return 'Бот работает', 200

if __name__ == '__main__':
    app.run()
