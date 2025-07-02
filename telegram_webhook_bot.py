from flask import Flask, request
import requests
import os
import openai

app = Flask(__name__)

# === Переменные среды ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
openai.api_key = os.environ.get("OPENAI_API_KEY")

# === Отправка сообщения в Telegram ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, data=data)

# === Webhook от TradingView ===
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    message = data.get('message', '📈 Сигнал от TradingView!')
    send_telegram_message(f"📢 <b>Сигнал:</b> {message}")
    return 'OK', 200

# === Проверка работоспособности ===
@app.route('/', methods=['GET'])
def index():
    return 'Бот работает', 200

# === GPT-анализ запроса ===
@app.route('/gpt', methods=['POST'])
def gpt_analysis():
    send_telegram_message("👀 Получен запрос на GPT-анализ, начинаю обработку...")

    data = request.json
    symbol = data.get("symbol", "EUR/USD")
    timeframe = data.get("timeframe", "M5")
    expiration = data.get("expiration", "5 минут")
    market_open = data.get("market_open", True)

    user_prompt = f"""
    Проанализируй валютную пару {symbol}.
    Таймфрейм: {timeframe}.
    Экспирация опциона: {expiration}.
    Рынок {'открыт' if market_open else 'закрыт'}.
    Используй стратегию: тренд по M30, вход по M5, учитывай VRVP, MA, уровни S/R, свечные паттерны.
    Выдай точку входа и краткое обоснование.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Ты торговый помощник по стратегии пользователя. Анализируешь сигналы и предлагаешь уровни входа по заданной системе."},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )

        gpt_reply = response['choices'][0]['message']['content']
        send_telegram_message(f"📊 GPT-АНАЛИЗ:\n{gpt_reply}")
        return 'OK', 200

    except Exception as e:
        send_telegram_message(f"⚠️ Ошибка GPT:\n{str(e)}")
        return 'Ошибка', 500

# === Запуск Flask-приложения ===
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
