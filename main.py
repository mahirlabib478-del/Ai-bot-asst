import os
import threading
from flask import Flask
import telebot
from telebot import types

# --- CONFIGURATION ---
TOKEN = "8786283279:AAHvKKt4pnL_JXMvru4TRwDn-1cGxWBqv2g"  # আপনার বটের টোকেন বসান
ADMIN_ID = 8538304896          # আপনার টেলিগ্রাম আইডি বসান

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- DATA STORAGE ---
items = {}            # Shop-এ থাকা আইটেম
sellable_types = {}   # বিক্রয়যোগ্য আইটেমের লিস্ট
user_balances = {}    
deposit_requests = {} 
user_sell_requests = {} 
deposit_number = "01339871504" 

# --- FLASK (Keep-Alive) ---
@app.route('/')
def home(): return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- HELPERS ---
def show_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Shop", "Sell", "Balance", "Deposit")
    bot.send_message(chat_id, "মূল মেনু:", reply_markup=markup)

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
    except: bot.reply_to(message, "⚠️ ব্যবহার: /setnumber 01xxxxxxxxx")

@bot.message_handler(commands=['addsellable'])
def add_sellable(message):
    if message.chat.id != ADMIN_ID: return
    try:
        p = message.text.replace("/addsellable ", "").split("|")
        sellable_types[p[0]] = int(p[1])
        bot.reply_to(message, f"✅ '{p[0]}' বিক্রিযোগ্য করা হয়েছে। দাম: {p[1]}")
    except: bot.reply_to(message, "⚠️ ফরম্যাট: /addsellable Name|Price")

# --- DEPOSIT FLOW ---
@bot.message_handler(func=lambda m: m.text == "Deposit")
def ask_amount(message):
    msg = bot.send_message(message.chat.id, "কত টাকা ডিপোজিট করবেন? (বাতিল করতে Cancel লিখুন)", reply_markup=get_cancel_markup())
    bot.register_next_step_handler(msg, process_amount)

def process_amount(message):
    if message.text == "Cancel": show_main_menu(message.chat.id); return
    deposit_requests[message.chat.id] = {"amount": message.text}
    markup = types.InlineKeyboardMarkup(); markup.add(types.InlineKeyboardButton("Done", callback_data="deposit_done"))
    bot.send_message(message.chat.id, f"বিকাশ: {deposit_number}\nটাকা পাঠিয়ে 'Done' বাটনে ক্লিক করুন।", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "deposit_done")
def ask_trx(call):
    msg = bot.send_message(call.from_user.id, "ট্রানজেকশন আইডি দিন (অথবা Cancel লিখুন):", reply_markup=get_cancel_markup())
    bot.register_next_step_handler(msg, finalize_deposit)

def finalize_deposit(message):
    if message.text == "Cancel": show_main_menu(message.chat.id); return
    uid = message.chat.id
    markup = types.InlineKeyboardMarkup(); markup.add(types.InlineKeyboardButton("Approve", callback_data=f"app_{uid}"))
    bot.send_message(ADMIN_ID, f"🔔 ডিপোজিট রিকোয়েস্ট!\nইউজার: {message.from_user.username}\nপরিমাণ: {deposit_requests[uid]['amount']}\nTrx: {message.text}", reply_markup=markup)
    bot.reply_to(message, "✅ অ্যাডমিনের কাছে পাঠানো হয়েছে।"); show_main_menu(uid)

# --- SELL FLOW ---
@bot.message_handler(func=lambda m: m.text == "Sell")
def show_sell(message):
    if not sellable_types: bot.send_message(message.chat.id, "❌ বর্তমানে কোনো আইটেম বিক্রির উপযোগী নেই।"); return
    markup = types.InlineKeyboardMarkup()
    for n, p in sellable_types.items(): markup.add(types.InlineKeyboardButton(f"{n} ({p} BDT)", callback_data=f"sell_{n}"))
    bot.send_message(message.chat.id, "বিক্রি করতে সিলেক্ট করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("sell_"))
def ask_sell_file(call):
    name = call.data.split("_")[1]
    user_sell_requests[call.from_user.id] = {"name": name}
    msg = bot.send_message(call.from_user.id, "আইটেমটি টেক্সট, ছবি বা ফাইল আকারে পাঠান:")
    bot.register_next_step_handler(msg, finalize_sell)

def finalize_sell(message):
    uid = message.chat.id
    f_id = message.photo[-1].file_id if message.photo else message.video.file_id if message.video else message.document.file_id if message.document else None
    f_type = 'photo' if message.photo else 'video' if message.video else 'document' if message.document else 'text'
    text = message.text if not f_id else "NoText"
    
    name = user_sell_requests[uid]["name"]
    markup = types.InlineKeyboardMarkup(); markup.add(types.InlineKeyboardButton("Approve", callback_data=f"appsell_{uid}_{name}_{f_id or 'None'}_{f_type}_{text}"))
    bot.send_message(ADMIN_ID, f"🔔 সেল রিকোয়েস্ট! আইটেম: {name}\nইউজার: {message.from_user.username}", reply_markup=markup)
    if f_id: bot.send_forward_message(ADMIN_ID, uid, message.message_id)
    bot.reply_to(message, "✅ পাঠানো হয়েছে।"); show_main_menu(uid)

# --- SHOP FLOW ---
@bot.message_handler(func=lambda m: m.text == "Shop")
def shop(message):
    if not items: bot.send_message(message.chat.id, "❌ বর্তমানে কোনো আইটেম নেই।"); return
    markup = types.InlineKeyboardMarkup()
    for n, d in items.items(): markup.add(types.InlineKeyboardButton(f"{n} ({d['price']} BDT)", callback_data=f"buy_{n}"))
    bot.send_message(message.chat.id, "পণ্য নির্বাচন করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_item(call):
    n = call.data.split("_", 1)[1]; uid = call.from_user.id; d = items[n]
    if user_balances.get(uid, 0) < d['price']: bot.send_message(uid, "❌ ব্যালেন্স কম!"); return
    user_balances[uid] -= d['price']
    if d['type'] == 'photo': bot.send_photo(uid, d['file_id'], caption=f"✅ সফল: {n}")
    elif d['type'] == 'video': bot.send_video(uid, d['file_id'], caption=f"✅ সফল: {n}")
    elif d['type'] == 'document': bot.send_document(uid, d['file_id'], caption=f"✅ সফল: {n}")
    else: bot.send_message(uid, f"✅ সফল: {n}\nকনটেন্ট: {d['text']}")

# --- APPROVALS & START ---
@bot.callback_query_handler(func=lambda call: call.data.startswith(("app_", "appsell_")))
def approve(call):
    if call.from_user.id != ADMIN_ID: return
    p = call.data.split("_", 5)
    if p[0] == "app":
        uid = int(p[1]); amount = int(deposit_requests[uid]['amount']); user_balances[uid] = user_balances.get(uid, 0) + amount
        bot.send_message(uid, "✅ ডিপোজিট এপ্রুভ হয়েছে!"); del deposit_requests[uid]
    else:
        uid, name, f_id, f_type, text = int(p[1]), p[2], p[3], p[4], p[5]
        items[name] = {"price": sellable_types[name], "file_id": f_id if f_id != 'None' else None, "type": f_type, "text": text}
        user_balances[uid] = user_balances.get(uid, 0) + sellable_types[name]
        bot.send_message(uid, f"✅ সেল এপ্রুভ হয়েছে এবং আইটেম শপে যোগ হয়েছে!");
    bot.edit_message_text("✅ Approved", call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['start'])
def start(message): show_main_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "Balance")
def bal(message): bot.send_message(message.chat.id, f"💰 ব্যালেন্স: {user_balances.get(message.chat.id, 0)} BDT")

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
