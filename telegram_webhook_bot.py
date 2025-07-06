# === telegram_webhook_bot.py ===

import os
import json
from flask import Flask, request
import telebot

# === Конфигурация ===
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # например: https://yourapp.onrender.com/telegram
USER_STATUS_FILE = 'user_status.json'

# === Инициализация ===
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# === Загрузка и сохранение статуса пользователей ===
def load_status():
    if os.path.exists(USER_STATUS_FILE):
        with open(USER_STATUS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_status():
    with open(USER_STATUS_FILE, 'w') as f:
        json.dump(user_status, f)

user_status = load_status()

# === Telegram команды ===
@bot.message_handler(commands=['start'])
def handle_start(msg):
    cid = str(msg.chat.id)
    user_status[cid] = {'enabled': True}
    save_status()
    bot.send_message(cid, "📡 Приём сигналов включён. Используй /off чтобы отключить.")

@bot.message_handler(commands=['on'])
def handle_on(msg):
    cid = str(msg.chat.id)
    user_status[cid] = {'enabled': True}
    save_status()
    bot.send_message(cid, "✅ Сигналы включены.")

@bot.message_handler(commands=['off'])
def handle_off(msg):
    cid = str(msg.chat.id)
    user_status[cid] = {'enabled': False}
    save_status()
    bot.send_message(cid, "⛔ Сигналы отключены.")

@bot.message_handler(commands=['status'])
def handle_status(msg):
    cid = str(msg.chat.id)
    state = user_status.get(cid, {}).get("enabled", False)
    status = "включены ✅" if state else "отключены ⛔"
    bot.send_message(cid, f"📊 Текущий статус: {status}")

# === Webhook от Telegram ===
@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return 'OK', 200

# === Webhook от TradingView ===
@app.route('/webhook', methods=['POST'])
def tradingview_webhook():
    data = request.get_json()
    if not data:
        return 'No data', 400

    text = format_signal(data)
    for cid, cfg in user_status.items():
        if cfg.get("enabled"):
            try:
                bot.send_message(cid, text, parse_mode='Markdown')
            except Exception as e:
                print(f"Ошибка при отправке в Telegram: {e}")

    return 'OK', 200

# === Форматирование сигнала ===
def format_signal(data):
    signal = data.get("signal", "SIGNAL")
    symbol = data.get("symbol", "UNKNOWN")
    tf = data.get("timeframe", "M?")
    return f"📈 *Сигнал*: `{signal}`\n💱 Инструмент: `{symbol}`\n🕒 Таймфрейм: `{tf}`"

# === Запуск приложения ===
if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=f'{WEBHOOK_URL}/telegram')
    app.run(host='0.0.0.0', port=10000)

