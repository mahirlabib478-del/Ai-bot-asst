import os
import threading
from flask import Flask
import telebot
from telebot import types

# --- CONFIG ---
TOKEN = "8786283279:AAHvKKt4pnL_JXMvru4TRwDn-1cGxWBqv2g"
ADMIN_ID = 8538304896  # Replace with your actual Telegram ID

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- IN-MEMORY STORAGE ---
items = {}            # {"ItemName": {"price": 100, "stock": 5, "text": "Content"}}
user_balances = {}    # {user_id: balance}
deposit_requests = {} # {user_id: {"step": 1, "bkash": "", "trx": "", "amount": 0}}

# --- FLASK (Keep-Alive) ---
@app.route('/')
def home(): return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- ADMIN: ADD ITEM ---
@bot.message_handler(commands=['additem'])
def add_item(message):
    if message.chat.id != ADMIN_ID: return
    try:
        # Format: /additem Name|Price|Stock|Content
        parts = message.text.replace("/additem ", "").split("|")
        name, price, stock, content = parts[0], int(parts[1]), int(parts[2]), parts[3]
        items[name] = {"price": price, "stock": stock, "text": content}
        bot.reply_to(message, f"✅ Added '{name}'. Stock: {stock}")
    except:
        bot.reply_to(message, "⚠️ Format: /additem Name|Price|Stock|Content")

# --- DEPOSIT SYSTEM ---
@bot.message_handler(commands=['deposit'])
def start_deposit(message):
    deposit_requests[message.chat.id] = {"step": 1}
    bot.send_message(message.chat.id, "Please enter your bKash number:")

@bot.message_handler(func=lambda m: m.chat.id in deposit_requests)
def handle_deposit_steps(message):
    uid = message.chat.id
    step = deposit_requests[uid].get("step")

    if step == 1:
        deposit_requests[uid]["bkash"] = message.text
        deposit_requests[uid]["step"] = 2
        bot.send_message(uid, "Great! Now enter your Transaction ID:")
    elif step == 2:
        deposit_requests[uid]["trx"] = message.text
        deposit_requests[uid]["step"] = 3
        bot.send_message(uid, "Enter the amount to add:")
    elif step == 3:
        try:
            amount = int(message.text)
            bkash = deposit_requests[uid]["bkash"]
            trx = deposit_requests[uid]["trx"]
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Approve", callback_data=f"approve_{uid}_{amount}"))
            
            bot.send_message(ADMIN_ID, f"🔔 New Deposit Request!\nUser: {uid}\nBkash: {bkash}\nTrxID: {trx}\nAmount: {amount} BDT", reply_markup=markup)
            bot.send_message(uid, "✅ Request submitted to admin. Please wait.")
            del deposit_requests[uid]
        except:
            bot.send_message(uid, "❌ Invalid amount. Please enter a number.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def approve_deposit(call):
    if call.message.chat.id != ADMIN_ID: return
    _, uid, amount = call.data.split("_")
    uid = int(uid)
    user_balances[uid] = user_balances.get(uid, 0) + int(amount)
    bot.send_message(uid, f"✅ Your deposit of {amount} BDT has been approved!")
    bot.edit_message_text("✅ Approved.", call.message.chat.id, call.message.message_id)

# --- SHOP & BALANCE ---
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Shop", "Balance")
    bot.send_message(message.chat.id, "Welcome to our shop!", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Balance")
def check_balance(message):
    bal = user_balances.get(message.chat.id, 0)
    bot.send_message(message.chat.id, f"💰 Your Balance: {bal} BDT\n\nUse /deposit to add funds.")

@bot.message_handler(func=lambda m: m.text == "Shop")
def shop(message):
    if not items:
        bot.send_message(message.chat.id, "❌ No items available.")
        return
    markup = types.InlineKeyboardMarkup()
    for name, item in items.items():
        markup.add(types.InlineKeyboardButton(f"{name} ({item['price']} BDT) - Stock: {item['stock']}", callback_data=f"buy_{name}"))
    bot.send_message(message.chat.id, "Available items:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_item(call):
    name = call.data.split("_", 1)[1]
    item = items[name]
    uid = call.message.chat.id
    
    if item['stock'] <= 0:
        bot.send_message(uid, "❌ Item out of stock!")
        return
    
    if user_balances.get(uid, 0) < item['price']:
        bot.send_message(uid, "❌ Insufficient balance.")
        return
    
    # Successful Purchase
    user_balances[uid] -= item['price']
    item['stock'] -= 1
    bot.send_message(uid, f"✅ Purchase Successful!\n\nItem: {name}\n\nContent:\n{item['text']}")

# --- EXECUTION ---
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
