import os
import threading
from flask import Flask
import telebot
from telebot import types

TOKEN = "8786283279:AAHvKKt4pnL_JXMvru4TRwDn-1cGxWBqv2g"
ADMIN_ID = 8538304896 

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

items = {}            
user_balances = {}    
deposit_requests = {} 
deposit_number = "01339871504" 

# --- FLASK ---
@app.route('/')
def home(): return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- HELPERS ---
def get_cancel_markup():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("Cancel")
    return markup

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['setnumber'])
def set_number(message):
    if message.chat.id != ADMIN_ID: return
    global deposit_number
    try:
        deposit_number = message.text.split()[1]
        bot.reply_to(message, f"✅ নতুন বিকাশ নম্বর: {deposit_number}")
    except:
        bot.reply_to(message, "⚠️ ব্যবহার: /setnumber 01xxxxxxxxx")

@bot.message_handler(commands=['additem'])
def add_item(message):
    if message.chat.id != ADMIN_ID: return
    try:
        parts = message.text.replace("/additem ", "").split("|")
        items[parts[0]] = {"price": int(parts[1]), "stock": int(parts[2]), "text": parts[3]}
        bot.reply_to(message, "✅ আইটেম যোগ হয়েছে।")
    except:
        bot.reply_to(message, "⚠️ ফরম্যাট: /additem Name|Price|Stock|Content")

# --- DEPOSIT FLOW ---
@bot.message_handler(func=lambda m: m.text == "Deposit")
def ask_amount(message):
    msg = bot.send_message(message.chat.id, "আপনি কত টাকা ডিপোজিট করতে চান?", reply_markup=get_cancel_markup())
    bot.register_next_step_handler(msg, process_amount)

def process_amount(message):
    if message.text == "Cancel":
        bot.send_message(message.chat.id, "অপারেশন বাতিল করা হয়েছে।", reply_markup=types.ReplyKeyboardRemove())
        return
    if not message.text.isdigit():
        bot.reply_to(message, "দয়া করে সঠিক সংখ্যা লিখুন।", reply_markup=get_cancel_markup())
        bot.register_next_step_handler(message, process_amount)
        return
    
    deposit_requests[message.chat.id] = {"amount": message.text}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Done", callback_data="deposit_done"))
    bot.send_message(message.chat.id, f"আমাদের বিকাশ নম্বর: {deposit_number}\nটাকা পাঠান এবং 'Done' বাটনে ক্লিক করুন।", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "deposit_done")
def ask_sender_number(call):
    msg = bot.send_message(call.from_user.id, "আপনি কোন নম্বর থেকে টাকা পাঠিয়েছেন?", reply_markup=get_cancel_markup())
    bot.register_next_step_handler(msg, ask_trx_id)

def ask_trx_id(message):
    if message.text == "Cancel":
        if message.chat.id in deposit_requests: del deposit_requests[message.chat.id]
        bot.send_message(message.chat.id, "বাতিল করা হয়েছে।", reply_markup=types.ReplyKeyboardRemove())
        return
    deposit_requests[message.chat.id]["sender_number"] = message.text
    msg = bot.send_message(message.chat.id, "Transaction ID দিন:")
    bot.register_next_step_handler(msg, finalize_deposit)

def finalize_deposit(message):
    if message.text == "Cancel":
        if message.chat.id in deposit_requests: del deposit_requests[message.chat.id]
        bot.send_message(message.chat.id, "বাতিল করা হয়েছে।", reply_markup=types.ReplyKeyboardRemove())
        return
    
    uid = message.chat.id
    deposit_requests[uid]["trx"] = message.text
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Approve", callback_data=f"app_{uid}"),
               types.InlineKeyboardButton("Deny", callback_data=f"deny_{uid}"))
    
    user = message.from_user
    username = f"@{user.username}" if user.username else "No Username"
    bot.send_message(ADMIN_ID, f"🔔 রিকোয়েস্ট!\nইউজার: {username} (ID: {uid})\nনম্বর: {deposit_requests[uid]['sender_number']}\nTrx: {message.text}\nপরিমাণ: {deposit_requests[uid]['amount']}", reply_markup=markup)
    bot.reply_to(message, "✅ রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে।", reply_markup=types.ReplyKeyboardRemove())

@bot.callback_query_handler(func=lambda call: call.data.startswith(("app_", "deny_")))
def handle_admin_decision(call):
    if call.from_user.id != ADMIN_ID: return
    try:
        _, uid = call.data.split("_")
        uid = int(uid)
        if uid not in deposit_requests:
            bot.answer_callback_query(call.id, "এটি ইতিমধ্যে প্রসেস করা হয়েছে!")
            return
            
        if call.data.startswith("app_"):
            amount = int(deposit_requests[uid]['amount'])
            user_balances[uid] = user_balances.get(uid, 0) + amount
            bot.send_message(uid, "✅ আপনার ডিপোজিট এপ্রুভ হয়েছে!")
            bot.edit_message_text("✅ Approved", call.message.chat.id, call.message.message_id)
        else:
            bot.send_message(uid, "❌ আপনার ডিপোজিট বাতিল করা হয়েছে।")
            bot.edit_message_text("❌ Denied", call.message.chat.id, call.message.message_id)
        del deposit_requests[uid]
    except Exception as e:
        bot.answer_callback_query(call.id, "কিছু ভুল হয়েছে!")

# --- SHOP & START ---
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Shop", "Balance", "Deposit")
    bot.send_message(message.chat.id, "স্বাগতম!", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Balance")
def check_balance(message):
    bal = user_balances.get(message.chat.id, 0)
    bot.send_message(message.chat.id, f"💰 আপনার ব্যালেন্স: {bal} BDT")

@bot.message_handler(func=lambda m: m.text == "Shop")
def shop(message):
    markup = types.InlineKeyboardMarkup()
    for name, data in items.items():
        markup.add(types.InlineKeyboardButton(f"{name} ({data['price']} BDT) - স্টক: {data['stock']}", callback_data=f"buy_{name}"))
    bot.send_message(message.chat.id, "পণ্য নির্বাচন করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_item(call):
    name = call.data.split("_", 1)[1]
    uid = call.from_user.id
    item = items[name]
    if item['stock'] <= 0:
        bot.answer_callback_query(call.id, "❌ আউট অফ স্টক!")
        return
    if user_balances.get(uid, 0) < item['price']:
        bot.send_message(uid, "❌ Insufficient balance.")
        return
    user_balances[uid] -= item['price']
    item['stock'] -= 1
    bot.send_message(uid, f"✅ কেনা সফল!\nপণ্য: {name}\nকনটেন্ট: {item['text']}")

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
