import os
import threading
import json
from flask import Flask
import telebot
from telebot import types

# --- CONFIGURATION ---
TOKEN = "8786283279:AAHvKKt4pnL_JXMvru4TRwDn-1cGxWBqv2g"
ADMIN_ID = 8538304896 
DATA_FILE = "shop_data.json"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- DATA MANAGEMENT ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"items": {}, "balances": {}, "pending_deposits": {}}
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

data = load_data()

# --- FLASK (To keep the bot alive) ---
@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- ADMIN: ADD STOCK ---
@bot.message_handler(commands=['additem'])
def add_item(message):
    if message.chat.id != ADMIN_ID: return
    try:
        # Format: /additem Name|Price|Stock|Content
        parts = message.text.replace("/additem ", "").split("|")
        name, price, stock, content = parts[0], int(parts[1]), int(parts[2]), parts[3]
        data['items'][name] = {"price": price, "stock": stock, "text": content}
        save_data(data)
        bot.reply_to(message, f"✅ '{name}' added/updated. Stock: {stock}")
    except:
        bot.reply_to(message, "⚠️ Format: /additem Name|Price|Stock|Content")

# --- USER: DEPOSIT REQUEST ---
@bot.message_handler(commands=['deposit'])
def request_deposit(message):
    try:
        amount = int(message.text.split()[1])
        req_id = f"{message.chat.id}_{len(data['pending_deposits'])}"
        data['pending_deposits'][req_id] = {"user_id": message.chat.id, "amount": amount}
        save_data(data)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Approve", callback_data=f"approve_{req_id}"))
        bot.send_message(ADMIN_ID, f"🔔 New Deposit: {amount} BDT from {message.chat.id}", reply_markup=markup)
        bot.reply_to(message, "✅ Request sent to admin.")
    except:
        bot.reply_to(message, "⚠️ Format: /deposit [Amount]")

# --- ADMIN: APPROVE DEPOSIT ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def approve_deposit(call):
    if call.message.chat.id != ADMIN_ID: return
    req_id = call.data.split("_", 1)[1]
    if req_id in data['pending_deposits']:
        req = data['pending_deposits'][req_id]
        uid = str(req['user_id'])
        data['balances'][uid] = data['balances'].get(uid, 0) + req['amount']
        del data['pending_deposits'][req_id]
        save_data(data)
        bot.send_message(uid, f"✅ Your deposit of {req['amount']} BDT was approved!")
        bot.edit_message_text("✅ Approved.", call.message.chat.id, call.message.message_id)

# --- SHOP & PURCHASING ---
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Shop", "Balance")
    bot.send_message(message.chat.id, "Welcome!", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Balance")
def check_balance(message):
    bal = data['balances'].get(str(message.chat.id), 0)
    bot.send_message(message.chat.id, f"💰 Balance: {bal} BDT")

@bot.message_handler(func=lambda m: m.text == "Shop")
def shop(message):
    markup = types.InlineKeyboardMarkup()
    for name, item in data['items'].items():
        markup.add(types.InlineKeyboardButton(f"{name} ({item['price']} BDT) | Stock: {item['stock']}", callback_data=f"buy_{name}"))
    bot.send_message(message.chat.id, "Available Items:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_item(call):
    name = call.data.split("_", 1)[1]
    item = data['items'][name]
    uid = str(call.message.chat.id)
    
    if item['stock'] <= 0:
        bot.answer_callback_query(call.id, "❌ Out of stock!")
        return
    
    if data['balances'].get(uid, 0) >= item['price']:
        data['balances'][uid] -= item['price']
        item['stock'] -= 1
        save_data(data)
        bot.send_message(uid, f"✅ Purchase Successful!\n\nContent: {item['text']}")
    else:
        bot.answer_callback_query(call.id, "❌ Insufficient balance!")

# --- EXECUTION ---
if __name__ == "__main__":
    # Start Flask in a separate thread so it doesn't block the bot
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
