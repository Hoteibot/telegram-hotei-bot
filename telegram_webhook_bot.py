import json
import os
from flask import Flask, request
import telebot
from telebot import types
from datetime import datetime

# === Настройки ===
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
USER_STATUS_FILE = 'user_status.json'

# === Flask-приложение ===
app = Flask(__name__)

# === Загрузка/Сохранение статуса пользователей ===
def load_status():
    if os.path.exists(USER_STATUS_FILE):
        with open(USER_STATUS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_status():
    with open(USER_STATUS_FILE, 'w') as f:
        json.dump(user_status, f, ensure_ascii=False, indent=2)

user_status = load_status()

# === Telegram-команды ===
@bot.message_handler(commands=['start'])
def start(msg):
    cid = str(msg.chat.id)
    name = msg.from_user.first_name or "Пользователь"
    if cid not in user_status:
        user_status[cid] = {
            "enabled": True,
            "name": name,
            "joined": datetime.now().strftime("%Y-%m-%d")
        }
        print(f"✅ Новый пользователь зарегистрирован: {name} ({cid})")
    else:
        user_status[cid]["enabled"] = True
        print(f"🔁 Пользователь повторно активировал бота: {name} ({cid})")
    save_status()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("▶️ ВКЛЮЧИТЬ"), types.KeyboardButton("⛔ ВЫКЛЮЧИТЬ"))

    bot.send_message(cid, "📡 Бот активен. Используй кнопки для управления приёмом сигналов.", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "▶️ ВКЛЮЧИТЬ")
def enable(msg):
    cid = str(msg.chat.id)
    if cid in user_status:
        user_status[cid]["enabled"] = True
        save_status()
        print(f"▶️ Сигналы включены для {cid}")
        bot.send_message(cid, "✅ Сигналы включены.")

@bot.message_handler(func=lambda msg: msg.text == "⛔ ВЫКЛЮЧИТЬ")
def disable(msg):
    cid = str(msg.chat.id)
    if cid in user_status:
        user_status[cid]["enabled"] = False
        save_status()
        print(f"⛔ Сигналы отключены для {cid}")
        bot.send_message(cid, "⛔ Сигналы отключены.")

@bot.message_handler(commands=['status'])
def status(msg):
    cid = str(msg.chat.id)
    cfg = user_status.get(cid)
    if cfg:
        state = "включены ✅" if cfg.get("enabled") else "отключены ⛔"
        bot.send_message(cid, f"💬 Сигналы {state}.")
    else:
        bot.send_message(cid, "❗ Вы ещё не зарегистрированы. Введите /start")

# === Webhook от Telegram ===
@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return 'OK', 200

# === Webhook от TradingView ===
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data:
        print("❌ Ошибка: данные не получены")
        return 'No data', 400

    text = format_signal(data)
    print("📩 Получен сигнал от TradingView:")
    print(text)
    print("👥 Отправка зарегистрированным пользователям...")

    for cid, cfg in user_status.items():
        print(f"→ {cid} ({cfg.get('name', 'Без имени')}): {'✅' if cfg.get('enabled') else '⛔'}")
        if cfg.get("enabled"):
            try:
                bot.send_message(cid, text, parse_mode='Markdown')
                print(f"✅ Сообщение отправлено пользователю {cid}")
            except Exception as e:
                print(f"❌ Ошибка отправки пользователю {cid}: {e}")

    return 'OK', 200

# === Форматирование сигнала ===
def format_signal(data):
    signal = data.get("signal", "")
    symbol = data.get("symbol", "?")
    tf = data.get("timeframe", "?")
    return f"🔔 Сигнал: *{signal.upper()}*\nИнструмент: `{symbol}`\nТаймфрейм: `{tf}`"

# === Запуск ===
if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url='https://telegram-hotei-bot.onrender.com/telegram')
    print("🚀 Бот запущен и webhook установлен.")
    app.run(host='0.0.0.0', port=10000)


