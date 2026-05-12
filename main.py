import os
import threading
from flask import Flask
import telebot
from telebot import types

# --- CONFIGURATION ---
TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_ID = 123456789 

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- STORAGE ---
items = {}            # কেনার আইটেম
sellable_types = {}   # বিক্রয়যোগ্য আইটেম
user_balances = {}    
deposit_requests = {} 
user_sell_requests = {} 
deposit_number = "01339871504" 

# --- FLASK ---
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

@bot.message_handler(commands=['additem'])
def ask_item(message):
    if message.chat.id != ADMIN_ID: return
    msg = bot.send_message(message.chat.id, "ফরম্যাট: Name|Price|Stock")
    bot.register_next_step_handler(msg, lambda m: save_item_p1(m))

def save_item_p1(message):
    try:
        data = message.text.split("|")
        bot.send_message(message.chat.id, "এখন ফাইলটি পাঠান:")
        bot.register_next_step_handler(message, lambda m: save_item_p2(m, data[0], data[1], data[2]))
    except: bot.reply_to(message, "ভুল ফরম্যাট!")

def save_item_p2(message, name, price, stock):
    f_id, f_type = (message.photo[-1].file_id, 'photo') if message.photo else (message.video.file_id, 'video') if message.video else (message.document.file_id, 'document') if message.document else (None, None)
    if f_id:
        items[name] = {"price": int(price), "stock": int(stock), "file_id": f_id, "type": f_type}
        bot.reply_to(message, "✅ আইটেম যোগ হয়েছে।")
    else: bot.reply_to(message, "❌ ফাইল পাওয়া যায়নি।")

@bot.message_handler(commands=['addsellable'])
def add_sellable(message):
    if message.chat.id != ADMIN_ID: return
    try:
        p = message.text.replace("/addsellable ", "").split("|")
        sellable_types[p[0]] = int(p[1])
        bot.reply_to(message, f"✅ '{p[0]}' বিক্রিযোগ্য করা হয়েছে।")
    except: bot.reply_to(message, "⚠️ ফরম্যাট: /addsellable Name|Price")

# --- DEPOSIT FLOW ---
@bot.message_handler(func=lambda m: m.text == "Deposit")
def ask_amount(message):
    msg = bot.send_message(message.chat.id, "কত টাকা ডিপোজিট করবেন? (Cancel লিখলে বাতিল হবে)", reply_markup=get_cancel_markup())
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
    markup = types.InlineKeyboardMarkup(); markup.add(types.InlineKeyboardButton("Approve", callback_data=f"app_{uid}"), types.InlineKeyboardButton("Deny", callback_data=f"deny_{uid}"))
    bot.send_message(ADMIN_ID, f"🔔 ডিপোজিট রিকোয়েস্ট!\nইউজার: {message.from_user.username}\nপরিমাণ: {deposit_requests[uid]['amount']}\nTrx: {message.text}", reply_markup=markup)
    bot.reply_to(message, "✅ অ্যাডমিনের কাছে পাঠানো হয়েছে।"); show_main_menu(uid)

# --- SELL & SHOP FLOW ---
@bot.message_handler(func=lambda m: m.text == "Sell")
def show_sell(message):
    if not sellable_types: bot.send_message(message.chat.id, "❌ কোনো আইটেম নেই।"); return
    markup = types.InlineKeyboardMarkup()
    for n, p in sellable_types.items(): markup.add(types.InlineKeyboardButton(f"{n} ({p} BDT)", callback_data=f"sell_{n}"))
    bot.send_message(message.chat.id, "বিক্রি করতে সিলেক্ট করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("sell_"))
def ask_sell_file(call):
    name = call.data.split("_")[1]
    user_sell_requests[call.from_user.id] = {"name": name}
    msg = bot.send_message(call.from_user.id, "ফাইলটি পাঠান:")
    bot.register_next_step_handler(msg, finalize_sell)

def finalize_sell(message):
    uid = message.chat.id
    f_id = message.photo[-1].file_id if message.photo else message.video.file_id if message.video else message.document.file_id if message.document else None
    if not f_id: bot.reply_to(message, "❌ ফাইল দিতে হবে!"); return
    name = user_sell_requests[uid]["name"]
    markup = types.InlineKeyboardMarkup(); markup.add(types.InlineKeyboardButton("Approve", callback_data=f"appsell_{uid}"))
    bot.send_message(ADMIN_ID, f"🔔 সেল রিকোয়েস্ট! আইটেম: {name}\nইউজার: {message.from_user.username}", reply_markup=markup)
    bot.send_forward_message(ADMIN_ID, uid, message.message_id)
    bot.reply_to(message, "✅ পাঠানো হয়েছে।"); show_main_menu(uid)

@bot.message_handler(func=lambda m: m.text == "Shop")
def shop(message):
    if not items: bot.send_message(message.chat.id, "❌ কোনো আইটেম নেই।"); return
    markup = types.InlineKeyboardMarkup()
    for n, d in items.items(): markup.add(types.InlineKeyboardButton(f"{n} ({d['price']} BDT)", callback_data=f"buy_{n}"))
    bot.send_message(message.chat.id, "পণ্য নির্বাচন করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_item(call):
    n = call.data.split("_")[1]; uid = call.from_user.id; d = items[n]
    if d['stock'] <= 0: bot.answer_callback_query(call.id, "❌ স্টক শেষ!"); return
    if user_balances.get(uid, 0) < d['price']: bot.send_message(uid, "❌ ব্যালেন্স কম!"); return
    user_balances[uid] -= d['price']; d['stock'] -= 1
    if d['type'] == 'photo': bot.send_photo(uid, d['file_id'], caption="✅ কেনা সফল!")
    elif d['type'] == 'video': bot.send_video(uid, d['file_id'], caption="✅ কেনা সফল!")
    else: bot.send_document(uid, d['file_id'], caption="✅ কেনা সফল!")

# --- APPROVALS ---
@bot.callback_query_handler(func=lambda call: call.data.startswith(("app_", "appsell_")))
def approve(call):
    if call.from_user.id != ADMIN_ID: return
    p = call.data.split("_")
    if p[0] == "app":
        uid = int(p[1]); amount = int(deposit_requests[uid]['amount']); user_balances[uid] = user_balances.get(uid, 0) + amount
        bot.send_message(uid, "✅ ডিপোজিট এপ্রুভ হয়েছে!"); del deposit_requests[uid]
    else:
        uid = int(p[1]); name = user_sell_requests[uid]['name']; price = sellable_types[name]
        user_balances[uid] = user_balances.get(uid, 0) + price
        bot.send_message(uid, f"✅ সেল এপ্রুভ হয়েছে! {price} BDT যোগ হয়েছে।")
    bot.edit_message_text("✅ Approved", call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['start'])
def start(message): show_main_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "Balance")
def bal(message): bot.send_message(message.chat.id, f"💰 ব্যালেন্স: {user_balances.get(message.chat.id, 0)} BDT")

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
