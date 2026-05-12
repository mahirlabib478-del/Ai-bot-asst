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

# --- HELPERS ---
def show_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Shop", "Sell", "Balance", "Deposit")
    bot.send_message(chat_id, "স্বাগতম! নিচে অপশন সিলেক্ট করুন:", reply_markup=markup)

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['addsellable'])
def add_sellable(message):
    if message.chat.id != ADMIN_ID: return
    try:
        data = message.text.replace("/addsellable ", "").split("|")
        sellable_types[data[0]] = int(data[1])
        bot.reply_to(message, f"✅ '{data[0]}' আইটেমটি সেল করার উপযোগী করা হয়েছে। দাম: {data[1]} BDT")
    except: bot.reply_to(message, "⚠️ ফরম্যাট ভুল! ব্যবহার করুন: /addsellable Name|Price")

# নতুন যোগ করা ফাংশন এখানে
@bot.message_handler(commands=['removeitem'])
def remove_item(message):
    if message.chat.id != ADMIN_ID: return
    try:
        item_name = message.text.split(" ", 1)[1]
        if item_name in items:
            del items[item_name]
            bot.reply_to(message, f"✅ '{item_name}' সফলভাবে শপ থেকে সরানো হয়েছে।")
        else:
            bot.reply_to(message, f"⚠️ '{item_name}' নামে শপে কোনো পণ্য নেই।")
    except IndexError:
        bot.reply_to(message, "⚠️ ব্যবহার: /removeitem Name")

# --- DEPOSIT SYSTEM ---
@bot.message_handler(func=lambda m: m.text == "Deposit")
def ask_amount(message):
    msg = bot.send_message(message.chat.id, "কত টাকা ডিপোজিট করবেন?")
    bot.register_next_step_handler(msg, process_amount)

def process_amount(message):
    deposit_requests[message.chat.id] = {"amount": message.text}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Done", callback_data="dep_done"))
    bot.send_message(message.chat.id, f"বিকাশ করুন: {deposit_number}\nটাকা পাঠানোর পর 'Done' বাটনে ক্লিক করুন।", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "dep_done")
def ask_trx(call):
    msg = bot.send_message(call.from_user.id, "ট্রানজেকশন আইডি (TrxID) লিখুন:")
    bot.register_next_step_handler(msg, finalize_deposit)

def finalize_deposit(message):
    uid = message.chat.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Approve", callback_data=f"app_{uid}"))
    markup.add(types.InlineKeyboardButton("Deny", callback_data=f"deny_{uid}"))
    bot.send_message(ADMIN_ID, f"🔔 ডিপোজিট রিকোয়েস্ট!\nইউজার: @{message.from_user.username}\nপরিমাণ: {deposit_requests[uid]['amount']}\nTrx: {message.text}", reply_markup=markup)
    bot.reply_to(message, "✅ রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে।")

# --- SELL SYSTEM ---
@bot.message_handler(func=lambda m: m.text == "Sell")
def show_sell(message):
    if not sellable_types: bot.send_message(message.chat.id, "❌ বর্তমানে কোনো আইটেম বিক্রির উপযোগী নেই।"); return
    markup = types.InlineKeyboardMarkup()
    for n, p in sellable_types.items(): markup.add(types.InlineKeyboardButton(f"{n} ({p} BDT)", callback_data=f"sell_{n}"))
    bot.send_message(message.chat.id, "আপনি কী বিক্রি করতে চান?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("sell_"))
def ask_sell_file(call):
    name = call.data.split("_", 1)[1]
    pending_sells[call.from_user.id] = {"name": name}
    msg = bot.send_message(call.from_user.id, "আইটেমটি ফাইল, ছবি, ভিডিও বা টেক্সট আকারে পাঠান:")
    bot.register_next_step_handler(msg, finalize_sell)

def finalize_sell(message):
    uid = message.chat.id
    name = pending_sells[uid]["name"]
    f_id = message.photo[-1].file_id if message.photo else message.video.file_id if message.video else message.document.file_id if message.document else None
    f_type = 'photo' if message.photo else 'video' if message.video else 'document' if message.document else 'text'
    text = message.caption or message.text or "No Description"
    pending_sells[uid].update({"f_id": f_id, "type": f_type, "text": text})
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Approve", callback_data=f"appsell_{uid}"))
    markup.add(types.InlineKeyboardButton("Deny", callback_data=f"denysell_{uid}"))
    bot.send_message(ADMIN_ID, f"🔔 সেল রিকোয়েস্ট!\nআইটেম: {name}\nইউজার: @{message.from_user.username}", reply_markup=markup)
    bot.reply_to(message, "✅ রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে।")

# --- SHOP & BUY SYSTEM ---
@bot.message_handler(func=lambda m: m.text == "Shop")
def shop(message):
    if not items: bot.send_message(message.chat.id, "❌ বর্তমানে শপে কোনো পণ্য নেই।"); return
    markup = types.InlineKeyboardMarkup()
    for n, d in items.items(): markup.add(types.InlineKeyboardButton(f"{n} ({d['price']} BDT)", callback_data=f"buy_{n}"))
    bot.send_message(message.chat.id, "পণ্য নির্বাচন করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_item(call):
    uid = call.from_user.id
    name = call.data.split("_", 1)[1]
    item = items[name]
    if user_balances.get(uid, 0) < item['price']:
        bot.answer_callback_query(call.id, "❌ আপনার ব্যালেন্স কম!"); return
    user_balances[uid] -= item['price']
    if item['type'] == 'photo': bot.send_photo(uid, item['f_id'], caption=f"✅ সফলভাবে কিনলেন: {name}")
    elif item['type'] == 'video': bot.send_video(uid, item['f_id'], caption=f"✅ সফলভাবে কিনলেন: {name}")
    elif item['type'] == 'document': bot.send_document(uid, item['f_id'], caption=f"✅ সফলভাবে কিনলেন: {name}")
    else: bot.send_message(uid, f"✅ সফলভাবে কিনলেন: {name}\nকনটেন্ট: {item['text']}")
    bot.answer_callback_query(call.id, "✅ কেনা সম্পন্ন হয়েছে!")

# --- APPROVAL & DENY LOGIC ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.from_user.id != ADMIN_ID: return
    data = call.data.split("_")
    action = data[0]
    uid = int(data[1])

    if action == "app":
        amount = int(deposit_requests[uid]['amount'])
        user_balances[uid] = user_balances.get(uid, 0) + amount
        bot.send_message(uid, "✅ আপনার ডিপোজিট এপ্রুভ হয়েছে!")
        del deposit_requests[uid]
    elif action == "appsell":
        info = pending_sells[uid]
        items[info['name']] = {"price": sellable_types[info['name']], "f_id": info['f_id'], "type": info['type'], "text": info['text']}
        user_balances[uid] = user_balances.get(uid, 0) + sellable_types[info['name']]
        bot.send_message(uid, "✅ আপনার সেল রিকোয়েস্ট এপ্রুভ হয়েছে!")
        del pending_sells[uid]
    elif action == "deny":
        bot.send_message(uid, "❌ দুঃখিত, আপনার ডিপোজিট রিকোয়েস্টটি ডিনাই করা হয়েছে।")
        del deposit_requests[uid]
    elif action == "denysell":
        bot.send_message(uid, "❌ দুঃখিত, আপনার সেল রিকোয়েস্টটি ডিনাই করা হয়েছে।")
        del pending_sells[uid]
    bot.edit_message_text(f"✅ Action Completed: {action}", call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['start'])
def start(message): show_main_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "Balance")
def bal(message): bot.send_message(message.chat.id, f"💰 ব্যালেন্স: {user_balances.get(message.chat.id, 0)} BDT")

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
