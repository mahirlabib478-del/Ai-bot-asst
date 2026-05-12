import os
import threading
from flask import Flask
import telebot
from telebot import types

TOKEN = "8786283279:AAHvKKt4pnL_JXMvru4TRwDn-1cGxWBqv2g"
ADMIN_ID = 8538304896 
deposit_number = "01339871504" # ডিফল্ট নম্বর

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

items = {}
user_balances = {}
deposit_requests = {} # {uid: {"amount": 0, "sender_number": "", "trx": ""}}

# --- FLASK (Keep-Alive) ---
@app.route('/')
def home(): return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['setnumber'])
def set_number(message):
    if message.chat.id != ADMIN_ID: return
    global deposit_number
    try:
        deposit_number = message.text.split()[1]
        bot.reply_to(message, f"✅ নতুন bKash নম্বর সেট করা হয়েছে: {deposit_number}")
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
    msg = bot.send_message(message.chat.id, "আপনি কত টাকা ডিপোজিট করতে চান?")
    bot.register_next_step_handler(msg, process_amount)

def process_amount(message):
    if not message.text.isdigit():
        bot.reply_to(message, "দয়া করে সঠিক সংখ্যা লিখুন।")
        return
    
    uid = message.chat.id
    deposit_requests[uid] = {"amount": message.text}
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Done", callback_data="deposit_done"))
    
    bot.send_message(uid, f"আমাদের bKash নম্বর: {deposit_number}\nএই নম্বরে টাকা পাঠান। টাকা পাঠানো হলে নিচের বাটনে ক্লিক করুন।", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "deposit_done")
def ask_sender_number(call):
    msg = bot.send_message(call.message.chat.id, "আপনি কোন নম্বর থেকে টাকা পাঠিয়েছেন?")
    bot.register_next_step_handler(msg, ask_trx_id)

def ask_trx_id(message):
    uid = message.chat.id
    deposit_requests[uid]["sender_number"] = message.text
    msg = bot.send_message(uid, "এখন আপনার Transaction ID টি দিন:")
    bot.register_next_step_handler(msg, finalize_deposit)

def finalize_deposit(message):
    uid = message.chat.id
    deposit_requests[uid]["trx"] = message.text
    req = deposit_requests[uid]
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Approve", callback_data=f"app_{uid}"),
               types.InlineKeyboardButton("Deny", callback_data=f"deny_{uid}"))
    
    user = message.from_user
    username = f"@{user.username}" if user.username else "No Username"
    
    bot.send_message(ADMIN_ID, f"🔔 নতুন ডিপোজিট রিকোয়েস্ট!\nইউজার: {username} (ID: {uid})\nনম্বর: {req['sender_number']}\nTrxID: {req['trx']}\nপরিমাণ: {req['amount']} BDT", reply_markup=markup)
    bot.reply_to(message, "✅ আপনার রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে।")

@bot.callback_query_handler(func=lambda call: call.data.startswith(("app_", "deny_")))
def handle_admin_decision(call):
    if call.message.chat.id != ADMIN_ID: return
    action, uid = call.data.split("_")
    uid = int(uid)
    
    if action == "app":
        amount = int(deposit_requests[uid]['amount'])
        user_balances[uid] = user_balances.get(uid, 0) + amount
        bot.send_message(uid, "✅ আপনার ডিপোজিট এপ্রুভ হয়েছে!")
        bot.edit_message_text("✅ Approved", call.message.chat.id, call.message.message_id)
    else:
        bot.send_message(uid, "❌ দুঃখিত, আপনার ডিপোজিট রিকোয়েস্টটি বাতিল করা হয়েছে।")
        bot.edit_message_text("❌ Denied", call.message.chat.id, call.message.message_id)
    
    if uid in deposit_requests: del deposit_requests[uid]

# --- STARTER ---
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Shop", "Balance", "Deposit")
    bot.send_message(message.chat.id, "স্বাগতম!", reply_markup=markup)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
