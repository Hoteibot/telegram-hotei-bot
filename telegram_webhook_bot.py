from flask import Flask, request
import requests
import os
import openai
import json

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
openai.api_key = os.environ.get("OPENAI_API_KEY")

# === Память для выбора пользователя ===
user_state = {}

# === Загрузка стратегий из JSON ===
def load_strategies():
    try:
        with open("strategies.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"default": "тренд по M30, вход по M5, VRVP, MA, уровни S/R, свечные паттерны."}

STRATEGIES = load_strategies()

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
            send_telegram_message("Привет! Я Hotei-bot-Аналитик. Вы спрашиваете — я отвечаю. Жми на /start", chat_id)
            show_symbol_keyboard(chat_id)

        elif text in SYMBOL_LIST:
            user_state.setdefault(chat_id, {})['symbol'] = text
            show_timeframe_keyboard(chat_id)

        elif text in ["M1", "M5", "M15"]:
            user_state.setdefault(chat_id, {})['timeframe'] = text
            show_expiration_keyboard(chat_id)

        elif text in ["3мин", "5мин", "7мин"]:
            user_state.setdefault(chat_id, {})['expiration'] = text
            show_session_keyboard(chat_id)

        elif text in SESSION_LIST:
            user_state.setdefault(chat_id, {})['session'] = text
            show_strategy_keyboard(chat_id)

        elif text in list(STRATEGIES.keys()):
            user_state.setdefault(chat_id, {})['strategy'] = text
            send_telegram_message("🔍 Выполняю анализ...", chat_id)
            run_gpt_analysis(chat_id)

        elif text == "🔁 Новый запрос" or text == "Готов к новому анализу:":
            user_state[chat_id] = {}
            show_symbol_keyboard(chat_id)

        else:
            keyboard = {
                "keyboard": [[{"text": "/start"}]],
                "resize_keyboard": True
            }
            send_telegram_message("Привет! Я Hotei-bot-Аналитик. Вы спрашиваете — я отвечаю. Жми на /start", chat_id, reply_markup=keyboard)

    return 'OK', 200

# === Список валютных пар ===
SYMBOL_LIST = [
    "AUD/JPY", "AUD/CHF", "AUD/CAD", "AUD/USD",
    "GBP/CAD", "GBP/CHF", "GBP/AUD", "GBP/JPY", "GBP/USD",
    "EUR/USD", "EUR/GBP", "EUR/CAD", "EUR/AUD", "EUR/JPY", "EUR/CHF",
    "USD/JPY", "USD/CAD", "USD/CHF",
    "CAD/CHF", "CAD/JPY", "CHF/JPY"
]

# === Список сессий ===
SESSION_LIST = ["Азиатская", "Европейская", "Американская"]

# === Показываем кнопки ===
def show_symbol_keyboard(chat_id):
    keyboard_rows = []
    row = []
    for i, symbol in enumerate(SYMBOL_LIST, 1):
        row.append({"text": symbol})
        if i % 3 == 0:
            keyboard_rows.append(row)
            row = []
    if row:
        keyboard_rows.append(row)

    keyboard = {
        "keyboard": keyboard_rows,
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

def show_session_keyboard(chat_id):
    keyboard = {
        "keyboard": [[{"text": s}] for s in SESSION_LIST],
        "resize_keyboard": True
    }
    send_telegram_message("Выбери торговую сессию:", chat_id, reply_markup=keyboard)

def show_strategy_keyboard(chat_id):
    strategy_buttons = [[{"text": name}] for name in STRATEGIES.keys()]
    keyboard = {
        "keyboard": strategy_buttons,
        "resize_keyboard": True
    }
    send_telegram_message("Выбери стратегию анализа:", chat_id, reply_markup=keyboard)

# === Запуск GPT анализа ===
def run_gpt_analysis(chat_id):
    state = user_state.get(chat_id, {})
    symbol = state.get("symbol", "EUR/USD")
    timeframe = state.get("timeframe", "M5")
    expiration = state.get("expiration", "5мин")
    session = state.get("session", "не указана")
    strategy_key = state.get("strategy", "default")
    strategy_text = STRATEGIES.get(strategy_key, STRATEGIES["default"])

    prompt = f"""
    Проанализируй валютную пару {symbol}.
    Таймфрейм: {timeframe}.
    Экспирация опциона: {expiration}.
    Торговая сессия: {session}.
    Рынок открыт.
    Используй стратегию: {strategy_text}
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
        keyboard = {
            "keyboard": [[{"text": "🔁 Новый запрос"}]],
            "resize_keyboard": True
        }
        send_telegram_message(f"📊 GPT-АНАЛИЗ:\n{reply}", chat_id)
        send_telegram_message("Готов к новому анализу:", chat_id, reply_markup=keyboard)
    except Exception as e:
        send_telegram_message(f"⚠️ GPT-ошибка:\n{str(e)}", chat_id)
        show_symbol_keyboard(chat_id)

# === Render Index ===
@app.route('/', methods=['GET'])
def index():
    return 'Бот работает', 200

# === Старт приложения ===
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
