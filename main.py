import os
import time
import threading
from flask import Flask
import telebot
from telebot import types

# CONFIG
TOKEN = "8786283279:AAHvKKt4pnL_JXMvru4TRwDn-1cGxWBqv2g"
ADMIN_ID = 8538304896 

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__) # MISSING: Flask app initialization

# Data Storage (In-memory)
items =[]  
user_balances = {} 

# --- FLASK ROUTE ---
# MISSING: This route is required to keep the bot alive on cloud platforms
@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['additem'])
def add_item(message):
    if message.chat.id != ADMIN_ID: return
    try:
        data = message.text.replace("/additem ", "").split("|")
        items.append({"name": data[0], "price": int(data[1]), "text": data[2]})
        bot.reply_to(message, "✅ Item added successfully!")
    except:
        bot.reply_to(message, "⚠️ Format: /additem Name|Price|Content")

@bot.message_handler(commands=['approve'])
def approve_balance(message):
    if message.chat.id != ADMIN_ID: return
    try:
        _, user_id, amount = message.text.split()
        user_id = int(user_id)
        user_balances[user_id] = user_balances.get(user_id, 0) + int(amount)
        bot.send_message(user_id, f"✅ Balance added: {amount} BDT")
        bot.reply_to(message, "✅ Done.")
    except:
        bot.reply_to(message, "⚠️ Format: /approve UserID Amount")

# --- USER COMMANDS ---
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Shop", "Balance")
    bot.send_message(message.chat.id, "Welcome to the Shop!", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Balance")
def check_balance(message):
    bal = user_balances.get(message.chat.id, 0)
    bot.send_message(message.chat.id, f"💰 Your Balance: {bal} BDT\n\nTo add balance, send money via Bkash and contact Admin.")

@bot.message_handler(func=lambda m: m.text == "Shop")
def shop(message):
    if not items:
        bot.send_message(message.chat.id, "❌ No items currently available.")
        return
    markup = types.InlineKeyboardMarkup()
    for i, item in enumerate(items):
        markup.add(types.InlineKeyboardButton(f"{item['name']} ({item['price']} BDT)", callback_data=f"buy_{i}"))
    bot.send_message(message.chat.id, "Select an item to buy:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_item(call):
    idx = int(call.data.split("_")[1])
    item = items[idx]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Confirm Purchase", callback_data=f"confirm_{idx}"))
    bot.send_message(call.message.chat.id, f"Buy '{item['name']}' for {item['price']} BDT?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm_purchase(call):
    idx = int(call.data.split("_")[1])
    item = items[idx]
    uid = call.message.chat.id
    
    if user_balances.get(uid, 0) >= item['price']:
        user_balances[uid] -= item['price']
        bot.send_message(uid, f"✅ Purchase Successful!\n\nContent: {item['text']}")
    else:
        bot.send_message(uid, "❌ Insufficient balance!")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # MISSING: Run flask in a thread so it doesn't block the bot polling
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
