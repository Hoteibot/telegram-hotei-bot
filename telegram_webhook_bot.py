from flask import Flask, request
import requests
import os
import openai

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
openai.api_key = os.environ.get("OPENAI_API_KEY")

# === Память для выбора пользователя ===
user_state = {}

# === Отправка сообщения в Telegram с кнопками ===
def send_telegram_message(message, chat_id, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    requests.post(url, json=data)

# === Webhook Telegram ===
@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    data = request.json

    if 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')

        if text == "/start":
            user_state[chat_id] = {}
            show_symbol_keyboard(chat_id)

        elif text in ["EUR/USD", "GBP/USD", "USD/JPY"]:
            user_state[chat_id]['symbol'] = text
            show_timeframe_keyboard(chat_id)

        elif text in ["M1", "M5", "M15"]:
            user_state[chat_id]['timeframe'] = text
            show_expiration_keyboard(chat_id)

        elif text in ["3мин", "5мин", "7мин"]:
            user_state[chat_id]['expiration'] = text
            send_telegram_message("🔍 Выполняю анализ...", chat_id)
            run_gpt_analysis(chat_id)

        else:
            send_telegram_message("Нажми /start, чтобы начать анализ", chat_id)

    return 'OK', 200

# === Показываем кнопки ===
def show_symbol_keyboard(chat_id):
    keyboard = {
        "keyboard": [[{"text": "EUR/USD"}, {"text": "GBP/USD"}, {"text": "USD/JPY"}]],
        "one_time_keyboard": True,
        "resize_keyboard": True
    }
    send_telegram_message("Выбери валютную пару:", chat_id, reply_markup=keyboard)

def show_timeframe_keyboard(chat_id):
    keyboard = {
        "keyboard": [[{"text": "M1"}, {"text": "M5"}, {"text": "M15"}]],
        "one_time_keyboard": True,
        "resize_keyboard": True
    }
    send_telegram_message("Выбери таймфрейм:", chat_id, reply_markup=keyboard)

def show_expiration_keyboard(chat_id):
    keyboard = {
        "keyboard": [[{"text": "3мин"}, {"text": "5мин"}, {"text": "7мин"}]],
        "one_time_keyboard": True,
        "resize_keyboard": True
    }
    send_telegram_message("Выбери время экспирации:", chat_id, reply_markup=keyboard)

# === Запуск GPT анализа ===
def run_gpt_analysis(chat_id):
    state = user_state.get(chat_id, {})
    symbol = state.get("symbol", "EUR/USD")
    timeframe = state.get("timeframe", "M5")
    expiration = state.get("expiration", "5мин")

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

# === Render Index ===
@app.route('/', methods=['GET'])
def index():
    return 'Бот работает', 200

# === Старт приложения ===
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
