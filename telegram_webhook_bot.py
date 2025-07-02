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
def send_telegram_message(message, chat_id=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id or CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, data=data)

# === Главная страница ===
@app.route('/', methods=['GET'])
def index():
    return 'Бот работает', 200

# === Webhook от TradingView ===
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    message = data.get('message', '📈 Сигнал от TradingView!')
    send_telegram_message(f"📢 <b>Сигнал:</b> {message}")
    return 'OK', 200

# === Обработка GPT-запроса от внешнего сервиса ===
@app.route('/gpt', methods=['POST'])
def gpt_analysis():
    send_telegram_message("👀 Получен внешний запрос на GPT-анализ...")

    data = request.json
    symbol = data.get("symbol", "EUR/USD")
    timeframe = data.get("timeframe", "M5")
    expiration = data.get("expiration", "5 минут")
    market_open = data.get("market_open", True)

    prompt = f"""
    Проанализируй валютную пару {symbol}.
    Таймфрейм: {timeframe}.
    Экспирация опциона: {expiration}.
    Рынок {'открыт' if market_open else 'закрыт'}.
    Используй стратегию: тренд по M30, вход по M5, VRVP, MA, уровни S/R, свечные паттерны.
    Выдай точку входа и краткое обоснование.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Ты торговый помощник по стратегии пользователя."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        reply = response['choices'][0]['message']['content']
        send_telegram_message(f"📊 GPT-АНАЛИЗ:\n{reply}")
        return 'OK', 200
    except Exception as e:
        send_telegram_message(f"⚠️ Ошибка GPT:\n{str(e)}")
        return 'Ошибка', 500

# === Обработка сообщений из Telegram ===
@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    data = request.json

    if 'message' in data:
        message = data['message']
        chat_id = message['chat']['id']
        text = message.get('text', '')

        if text.startswith('/анализ'):
            parts = text.strip().split()
            if len(parts) == 4:
                _, symbol, timeframe, expiration = parts

                prompt = f"""
                Проанализируй валютную пару {symbol}.
                Таймфрейм: {timeframe}.
                Экспирация опциона: {expiration}.
                Рынок открыт.
                Используй стратегию: тренд по M30, вход по M5, VRVP, MA, уровни S/R, свечные паттерны.
                Выдай точку входа и краткое обоснование.
                """

                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "Ты торговый помощник по стратегии пользователя."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=500,
                        temperature=0.7
                    )
                    reply = response['choices'][0]['message']['content']
                    send_telegram_message(f"📊 GPT-АНАЛИЗ:\n{reply}", chat_id)
                except Exception as e:
                    send_telegram_message(f"⚠️ GPT-ошибка:\n{str(e)}", chat_id)
            else:
                send_telegram_message("⚠️ Формат команды:\n/анализ EUR/USD M5 5мин", chat_id)

    return 'OK', 200

# === Запуск сервера (Render сам использует этот блок) ===
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

