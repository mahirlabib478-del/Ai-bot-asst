import os
import threading
from flask import Flask
import telebot
from telebot import types

# --- CONFIGURATION ---
TOKEN = "8786283279:AAHvKKt4pnL_JXMvru4TRwDn-1cGxWBqv2g"
ADMIN_ID = 8538304896

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- DATA STORAGE ---
items = {}            
sellable_types = {}   
user_balances = {}    
deposit_requests = {} 
pending_sells = {}    
deposit_number = "01339871504" 

# --- FLASK ---
@app.route('/')
def home(): return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['addsellable'])
def add_sellable(message):
    if message.chat.id != ADMIN_ID: return
    try:
        data = message.text.replace("/addsellable ", "").split("|")
        sellable_types[data[0]] = int(data[1])
        bot.reply_to(message, f"✅ '{data[0]}' সেল করার উপযোগী করা হয়েছে। দাম: {data[1]} BDT")
    except: bot.reply_to(message, "⚠️ ফরম্যাট: /addsellable Name|Price")

# --- নতুন রিমুভ সিস্টেম (এখানেই যোগ করা হয়েছে) ---
@bot.message_handler(commands=['remove'])
def remove_menu(message):
    if message.chat.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Remove from Shop", callback_data="rem_shop"))
    markup.add(types.InlineKeyboardButton("Remove from Sellable List", callback_data="rem_sell"))
    bot.send_message(message.chat.id, "কি রিমুভ করতে চান?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rem_"))
def handle_remove_selection(call):
    if call.from_user.id != ADMIN_ID: return
    mode = call.data.split("_")[1]
    if mode == "shop":
        if not items: bot.edit_message_text("শপ খালি!", call.message.chat.id, call.message.message_id); return
        markup = types.InlineKeyboardMarkup()
        for n in items.keys(): markup.add(types.InlineKeyboardButton(f"Remove {n}", callback_data=f"del_shop_{n}"))
        bot.edit_message_text("শপ থেকে কোনটি রিমুভ করবেন?", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif mode == "sell":
        if not sellable_types: bot.edit_message_text("সেল লিস্ট খালি!", call.message.chat.id, call.message.message_id); return
        markup = types.InlineKeyboardMarkup()
        for n in sellable_types.keys(): markup.add(types.InlineKeyboardButton(f"Remove {n}", callback_data=f"del_sell_{n}"))
        bot.edit_message_text("সেল লিস্ট থেকে কোনটি রিমুভ করবেন?", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def confirm_remove(call):
    _, mode, name = call.data.split("_", 2)
    if mode == "shop" and name in items: del items[name]
    elif mode == "sell" and name in sellable_types: del sellable_types[name]
    bot.edit_message_text(f"✅ '{name}' রিমুভ করা হয়েছে।", call.message.chat.id, call.message.message_id)

# --- (বাকি আগের কোডগুলো এখানে থাকবে) ---
@bot.message_handler(func=lambda m: m.text == "Deposit")
def ask_amount(message):
    msg = bot.send_message(message.chat.id, "কত টাকা ডিপোজিট করবেন?")
    bot.register_next_step_handler(msg, lambda m: process_amount(m))

def process_amount(message):
    deposit_requests[message.chat.id] = {"amount": message.text}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Done", callback_data="dep_done"))
    bot.send_message(message.chat.id, f"বিকাশ করুন: {deposit_number}\nটাকা পাঠিয়ে 'Done' বাটনে ক্লিক করুন।", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "dep_done")
def ask_trx(call):
    msg = bot.send_message(call.from_user.id, "ট্রানজেকশন আইডি দিন:")
    bot.register_next_step_handler(msg, finalize_deposit)

def finalize_deposit(message):
    uid = message.chat.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Approve", callback_data=f"app_{uid}"))
    markup.add(types.InlineKeyboardButton("Deny", callback_data=f"deny_{uid}"))
    bot.send_message(ADMIN_ID, f"🔔 ডিপোজিট! User: @{message.from_user.username}\nAmount: {deposit_requests[uid]['amount']}\nTrx: {message.text}", reply_markup=markup)
    bot.reply_to(message, "✅ রিকোয়েস্ট পাঠানো হয়েছে।")

@bot.message_handler(func=lambda m: m.text == "Sell")
def show_sell(message):
    if not sellable_types: bot.send_message(message.chat.id, "❌ কোনো আইটেম বিক্রির উপযোগী নেই।"); return
    markup = types.InlineKeyboardMarkup()
    for n, p in sellable_types.items(): markup.add(types.InlineKeyboardButton(f"{n} ({p} BDT)", callback_data=f"sell_{n}"))
    bot.send_message(message.chat.id, "পণ্য নির্বাচন করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("sell_"))
def ask_sell_file(call):
    name = call.data.split("_", 1)[1]
    pending_sells[call.from_user.id] = {"name": name}
    msg = bot.send_message(call.from_user.id, "ফাইল বা টেক্সট পাঠান:")
    bot.register_next_step_handler(msg, finalize_sell)

def finalize_sell(message):
    uid = message.chat.id
    name = pending_sells[uid]["name"]
    f_id = message.photo[-1].file_id if message.photo else message.video.file_id if message.video else message.document.file_id if message.document else None
    f_type = 'photo' if message.photo else 'video' if message.video else 'document' if message.document else 'text'
    pending_sells[uid].update({"f_id": f_id, "type": f_type, "text": message.text})
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Approve", callback_data=f"appsell_{uid}"))
    markup.add(types.InlineKeyboardButton("Deny", callback_data=f"denysell_{uid}"))
    bot.send_message(ADMIN_ID, f"🔔 সেল রিকোয়েস্ট: {name}\nUser: @{message.from_user.username}", reply_markup=markup)
    bot.reply_to(message, "✅ পাঠানো হয়েছে।")

@bot.message_handler(func=lambda m: m.text == "Shop")
def shop(message):
    if not items: bot.send_message(message.chat.id, "❌ শপ খালি।"); return
    markup = types.InlineKeyboardMarkup()
    for n, d in items.items(): markup.add(types.InlineKeyboardButton(f"{n} ({d['price']} BDT)", callback_data=f"buy_{n}"))
    bot.send_message(message.chat.id, "পণ্য নির্বাচন করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_item(call):
    uid = call.from_user.id
    name = call.data.split("_", 1)[1]
    item = items[name]
    if user_balances.get(uid, 0) < item['price']: bot.answer_callback_query(call.id, "❌ ব্যালেন্স কম!"); return
    user_balances[uid] -= item['price']
    if item['type'] == 'photo': bot.send_photo(uid, item['f_id'], caption=f"✅ কেনা সম্পন্ন: {name}")
    elif item['type'] == 'video': bot.send_video(uid, item['f_id'], caption=f"✅ কেনা সম্পন্ন: {name}")
    elif item['type'] == 'document': bot.send_document(uid, item['f_id'], caption=f"✅ কেনা সম্পন্ন: {name}")
    else: bot.send_message(uid, f"✅ কেনা সম্পন্ন: {name}\nকনটেন্ট: {item['text']}")
    bot.answer_callback_query(call.id, "✅ কেনা হয়েছে!")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.from_user.id != ADMIN_ID: return
    if call.data.startswith(("app_", "appsell_", "deny_", "denysell_")):
        data = call.data.split("_")
        action, uid = data[0], int(data[1])
        if action == "app":
            amount = int(deposit_requests[uid]['amount'])
            user_balances[uid] = user_balances.get(uid, 0) + amount
            bot.send_message(uid, "✅ ডিপোজিট এপ্রুভ হয়েছে!")
            del deposit_requests[uid]
        elif action == "appsell":
            info = pending_sells[uid]
            items[info['name']] = {"price": sellable_types[info['name']], "f_id": info['f_id'], "type": info['type'], "text": info['text']}
            user_balances[uid] = user_balances.get(uid, 0) + sellable_types[info['name']]
            bot.send_message(uid, "✅ সেল এপ্রুভ হয়েছে!"); del pending_sells[uid]
        elif action == "deny": bot.send_message(uid, "❌ ডিপোজিট রিজেক্ট হয়েছে!"); del deposit_requests[uid]
        elif action == "denysell": bot.send_message(uid, "❌ সেল রিজেক্ট হয়েছে!"); del pending_sells[uid]
        bot.edit_message_text(f"✅ Action Done", call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Shop", "Sell", "Balance", "Deposit")
    bot.send_message(message.chat.id, "মূল মেনু:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Balance")
def bal(message): bot.send_message(message.chat.id, f"💰 ব্যালেন্স: {user_balances.get(message.chat.id, 0)} BDT")

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
