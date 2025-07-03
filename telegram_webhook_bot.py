from flask import Flask, request
import requests
import os
import openai
import json
import csv
import urllib.request
from datetime import datetime

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
openai.api_key = os.environ.get("OPENAI_API_KEY")

# === Память для выбора пользователя ===
user_state = {}

# === ID и GID вкладок Google Sheets ===
GOOGLE_SHEET_ID = "1p4rAh1zPKF-BHeLOXBqvUk7zSKb-ayz8BAtvzF9n1aQ"
SHEET_GIDS = {
    "Трендовая": "0",
    "Контртрендовая": "1407798106",
    "Диапазонная": "393811242",
    "Hotei": "879338379",
    "Анализ по умолчанию": "1281083042"
}

# === Загрузка стратегий по GID вкладки ===
def load_strategies_by_gid(gid):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv&gid={gid}"
        with urllib.request.urlopen(url) as response:
            lines = [l.decode('utf-8') for l in response.readlines()]
            reader = csv.DictReader(lines)
            return {row['Название']: row['Описание'] for row in reader if row.get('Название') and row.get('Описание')}
    except Exception as e:
        return {}

STRATEGIES = {}

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

# === Вспомогательная функция — проверка текущей сессии ===
def get_active_sessions():
    now = datetime.utcnow().hour
    sessions = []
    if 0 <= now < 9:
        sessions.append("Азиатская")
    if 7 <= now < 17:
        sessions.append("Европейская")
    if 13 <= now < 22:
        sessions.append("Американская")
    return sessions

# === Webhook Telegram ===
@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    data = request.json

    if 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')

        state = user_state.setdefault(chat_id, {})

        if text == "/start":
            send_telegram_message("Привет! Я Hotei-bot-Аналитик. Вы спрашиваете — я отвечаю. Жми на /start", chat_id)
            show_main_menu(chat_id)

        elif text == "⚙️ Настройки":
            show_settings_menu(chat_id)

        elif text == "Выбор валютной пары":
            show_symbol_menu(chat_id)

        elif text == "Выбор таймфрейма":
            show_timeframe_menu(chat_id)

        elif text == "Выбор экспирации":
            show_expiration_menu(chat_id)

        elif text == "Выбор стратегии":
            show_strategy_category_menu(chat_id)

        elif text == "◀️ Назад":
            show_main_menu(chat_id)

        elif text in SYMBOL_LIST:
            state['symbol'] = text
            send_telegram_message(f"✅ Валютная пара выбрана: {text}", chat_id)
            show_main_menu(chat_id)

        elif text in ["M1", "M5", "M15"]:
            state['timeframe'] = text
            send_telegram_message(f"✅ Таймфрейм установлен: {text}", chat_id)
            show_settings_menu(chat_id)

        elif text in ["3мин", "5мин", "7мин"]:
            state['expiration'] = text
            send_telegram_message(f"✅ Экспирация установлена: {text}", chat_id)
            show_settings_menu(chat_id)

        elif text in SHEET_GIDS:
            state['strategy_category'] = text
            global STRATEGIES
            STRATEGIES = load_strategies_by_gid(SHEET_GIDS[text])
            if STRATEGIES:
                show_strategy_keyboard(chat_id)
            else:
                send_telegram_message("⚠️ В этой категории пока нет доступных стратегий. Попробуй другую.", chat_id)

        elif text in list(STRATEGIES.keys()):
            state['strategy'] = text
            send_telegram_message(f"✅ Стратегия установлена: {text}", chat_id)
            show_settings_menu(chat_id)

        elif text == "▶️ Начать анализ":
            summary = f"<b>Выбранные параметры:</b>\n\n📊 Стратегия: {state.get('strategy', 'не выбрана')}\n🕐 Таймфрейм: {state.get('timeframe', 'не выбран')}\n⏳ Экспирация: {state.get('expiration', 'не выбрана')}\n💱 Валюта: {state.get('symbol', 'не выбрана')}"
            send_telegram_message(summary, chat_id)
            send_telegram_message("🔍 Выполняю анализ...", chat_id)
            run_gpt_analysis(chat_id)

        elif text == "🔁 Новый запрос" or text == "Готов к новому анализу:":
            show_symbol_menu(chat_id)

        else:
            keyboard = {
                "keyboard": [[{"text": "/start"}]],
                "resize_keyboard": True
            }
            send_telegram_message("Привет! Я Hotei-bot-Аналитик. Вы спрашиваете — я отвечаю. Жми на /start", chat_id, reply_markup=keyboard)

    return 'OK', 200

# === Списки для выбора ===
SYMBOL_LIST = [
    "AUD/JPY", "AUD/CHF", "AUD/CAD", "AUD/USD",
    "GBP/CAD", "GBP/CHF", "GBP/AUD", "GBP/JPY", "GBP/USD",
    "EUR/USD", "EUR/GBP", "EUR/CAD", "EUR/AUD", "EUR/JPY", "EUR/CHF",
    "USD/JPY", "USD/CAD", "USD/CHF",
    "CAD/CHF", "CAD/JPY", "CHF/JPY"
]

SESSION_LIST = ["Азиатская", "Европейская", "Американская"]

# === Меню и кнопки ===
def show_main_menu(chat_id):
    keyboard = {
        "keyboard": [
            [{"text": "▶️ Начать анализ"}],
            [{"text": "⚙️ Настройки"}]
        ],
        "resize_keyboard": True
    }
    send_telegram_message("Выбери действие:", chat_id, reply_markup=keyboard)

def show_settings_menu(chat_id):
    keyboard = {
        "keyboard": [
            [{"text": "Выбор таймфрейма"}],
            [{"text": "Выбор экспирации"}],
            [{"text": "Выбор стратегии"}],
            [{"text": "◀️ Назад"}]
        ],
        "resize_keyboard": True
    }
    send_telegram_message("Настройки:", chat_id, reply_markup=keyboard)

def show_symbol_menu(chat_id):
    buttons = [[{"text": pair}] for pair in SYMBOL_LIST]
    keyboard = {
        "keyboard": buttons,
        "resize_keyboard": True
    }
    send_telegram_message("Выбери валютную пару:", chat_id, reply_markup=keyboard)

def show_timeframe_menu(chat_id):
    keyboard = {
        "keyboard": [[{"text": "M1"}, {"text": "M5"}, {"text": "M15"}], [{"text": "◀️ Назад"}]],
        "resize_keyboard": True
    }
    send_telegram_message("Выбери таймфрейм:", chat_id, reply_markup=keyboard)

def show_expiration_menu(chat_id):
    keyboard = {
        "keyboard": [[{"text": "3мин"}, {"text": "5мин"}, {"text": "7мин"}], [{"text": "◀️ Назад"}]],
        "resize_keyboard": True
    }
    send_telegram_message("Выбери время экспирации:", chat_id, reply_markup=keyboard)

def show_strategy_category_menu(chat_id):
    buttons = [[{"text": key}] for key in SHEET_GIDS.keys()]
    buttons.append([{"text": "◀️ Назад"}])
    keyboard = {
        "keyboard": buttons,
        "resize_keyboard": True
    }
    send_telegram_message("Выбери категорию стратегии:", chat_id, reply_markup=keyboard)

def show_strategy_keyboard(chat_id):
    strategy_buttons = [[{"text": name}] for name in STRATEGIES.keys()]
    strategy_buttons.append([{"text": "◀️ Назад"}])
    keyboard = {
        "keyboard": strategy_buttons,
        "resize_keyboard": True
    }
    send_telegram_message("Выбери стратегию анализа:", chat_id, reply_markup=keyboard)

# === Анализ ===
def run_gpt_analysis(chat_id):
    state = user_state.get(chat_id, {})
    symbol = state.get("symbol", "EUR/USD")
    timeframe = state.get("timeframe", "M5")
    expiration = state.get("expiration", "5мин")
    session = get_active_sessions()
    session = session[0] if session else "не определена"
    strategy_key = state.get("strategy", "default")
    strategy_text = STRATEGIES.get(strategy_key, STRATEGIES.get("default", ""))

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
        show_main_menu(chat_id)

# === Render Index ===
@app.route('/', methods=['GET'])
def index():
    return 'Бот работает', 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

@app.route('/tv-signal', methods=['POST'])
def handle_tv_signal():
    data = request.json
    chat_id = os.environ.get("CHAT_ID")  # Можно заменить на ID канала или сделать рассылку

    symbol = data.get("symbol", "EUR/USD")
    signal_type = data.get("signal", "BUY")  # BUY или SELL
    timeframe = data.get("timeframe", "M5")

    # Стратегия по умолчанию
    strategy_key = "Анализ по умолчанию"
    strategy_text = STRATEGIES.get(strategy_key, "")

    # Пример: анализ через GPT
    prompt = f"""
    Получен сигнал из TradingView: {signal_type} по валютной паре {symbol} на таймфрейме {timeframe}.
    Используй стратегию: {strategy_text}.
    Проанализируй, насколько сигнал оправдан. Подтверди или отклони.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Ты торговый помощник. Анализируешь сигналы и даешь вывод."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.6
        )
        gpt_reply = response['choices'][0]['message']['content']
        send_telegram_message(f"📥 <b>Сигнал от TradingView</b>\nПара: {symbol}\nСигнал: {signal_type}\nТФ: {timeframe}\n\n🧠 GPT мнение:\n{gpt_reply}", chat_id)
        return 'OK', 200
    except Exception as e:
        send_telegram_message(f"⚠️ Ошибка при анализе сигнала из TV:\n{str(e)}", chat_id)
        return 'Ошибка GPT', 500
