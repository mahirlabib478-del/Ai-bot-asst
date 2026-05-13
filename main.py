import os 
import threading 
from flask import Flask 
import telebot 
from telebot import types
import json

# --- CONFIGURATION ---

TOKEN = "8786283279:AAHvKKt4pnL_JXMvru4TRwDn-1cGxWBqv2g" 
ADMIN_ID = 8538304896

import json
# আপনার প্রাইভেট চ্যানেলের আইডি এখানে দিন
CHANNEL_ID = -1003903695158

bot = telebot.TeleBot(TOKEN) 
# # ডাটা লোড করার ফাংশন
def load_data():
    try:
        # মেসেজ হিস্ট্রি থেকে ডাটা নেওয়ার চেষ্টা করা
        messages = bot.get_chat_history(CHANNEL_ID, limit=1)
        if messages and len(messages) > 0:
            return json.loads(messages[0].text)
    except Exception as e:
        print(f"Load Error: {e}")
    # যদি চ্যানেলে কোনো মেসেজ না থাকে, তবে একটি প্রাথমিক মেসেজ পাঠিয়ে আইডি সেট করা
    print("No data found, starting fresh.")
    return {"items": {}, "sellable": {}, "balances": {}, "users": {}}

# ডাটা সেভ করার ফাংশন
save_lock = threading.Lock()
def save_data():
    with save_lock:
        data = {"items": items, "sellable": sellable_types, "balances": user_balances, "users": users_db}
        data_str = json.dumps(data)
        try:
            messages = bot.get_chat_history(CHANNEL_ID, limit=1)
            if messages and len(messages) > 0:
                # আগের মেসেজ থাকলে তা এডিট করা
                bot.edit_message_text(data_str, CHANNEL_ID, messages[0].message_id)
            else:
                # মেসেজ না থাকলে নতুন করে পাঠানো
                bot.send_message(CHANNEL_ID, data_str)
        except Exception as e:
            print(f"Save Error: {e}")
            
app = Flask(__name__)

# --- DATA STORAGE ---
saved_data = load_data() 
items = saved_data.get("items", {})
sellable_types = saved_data.get("sellable", {})
user_balances = saved_data.get("balances", {})
users_db = saved_data.get("users", {})

deposit_requests = {}
withdraw_requests = {} 
pending_sells = {} 
deposit_number = "01339871504"

# --- FLASK (Keep-Alive) ---

@app.route('/') 
def home(): return "Bot is running!"

def run_flask(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- ADMIN COMMANDS: BKASH CHANGE ---

@bot.message_handler(commands=['setbkash']) 
def set_bkash(message): 
    if message.chat.id != ADMIN_ID: return 
    global deposit_number 
    try: 
        new_num = message.text.split(" ")[1] 
        deposit_number = new_num 
        bot.reply_to(message, f"✅ বিকাশ নাম্বার আপডেট হয়েছে: {deposit_number}") 
    except: 
        bot.reply_to(message, "⚠️ ফরম্যাট: /setbkash 01xxxxxxxxx")

# --- ADMIN COMMANDS: ADD ---

@bot.message_handler(commands=['addsellable']) 
def add_sellable(message): 
    if message.chat.id != ADMIN_ID: return 
    try: 
        data = message.text.replace("/addsellable ", "").split("|") 
        sellable_types[data[0]] = {"price": int(data[1])} 
        save_data()
        bot.reply_to(message, f"✅ '{data[0]}' সেলে যোগ হয়েছে। দাম: {data[1]} BDT") 
    except: 
        bot.reply_to(message, "⚠️ ফরম্যাট: /addsellable Name|Price")

@bot.message_handler(commands=['additem']) 
def add_item_admin(message): 
    if message.chat.id != ADMIN_ID: return 
    if not message.reply_to_message: 
        bot.reply_to(message, "⚠️ ফাইল/টেক্সট রিফ্লাই দিয়ে লিখুন: /additem Name|Price|Stock") 
        return 
    try: 
        data = message.text.replace("/additem ", "").split("|") 
        name, price, stock = data[0], int(data[1]), int(data[2]) 
        msg = message.reply_to_message 
        f_id = msg.photo[-1].file_id if msg.photo else msg.video.file_id if msg.video else msg.document.file_id if msg.document else None 
        f_type = 'photo' if msg.photo else 'video' if msg.video else 'document' if msg.document else 'text' 
        text = msg.caption or msg.text or "No content" 
        items[name] = {"price": price, "stock": stock, "f_id": f_id, "type": f_type, "text": text} 
        save_data()
        bot.reply_to(message, f"✅ '{name}' {stock} স্টক সহ শপে যোগ হয়েছে।") 
    except Exception as e: 
        bot.reply_to(message, f"❌ ফরম্যাট ভুল! ব্যবহার করুন: /additem Name|Price|Stock\nError: {e}")

@bot.message_handler(commands=['setstock']) 
def set_stock_admin(message): 
    if message.chat.id != ADMIN_ID: return 
    try: 
        data = message.text.replace("/setstock ", "").split("|") 
        name, new_stock = data[0], int(data[1]) 
        if name in items: 
            items[name]['stock'] = new_stock 
            save_data()
            bot.reply_to(message, f"✅ '{name}' এর নতুন স্টক: {new_stock}") 
        else: 
            bot.reply_to(message, "❌ এই আইটেমটি শপে নেই।") 
    except: 
        bot.reply_to(message, "⚠️ ফরম্যাট: /setstock Name|NewStock")

# --- ADMIN COMMANDS: REMOVE (FIXED) ---

@bot.message_handler(commands=['remove']) 
def remove_menu(message): 
    if message.chat.id != ADMIN_ID: return 
    markup = types.InlineKeyboardMarkup() 
    markup.add( types.InlineKeyboardButton("Remove from Shop", callback_data="rem_shop"), types.InlineKeyboardButton("Remove from Sellable List", callback_data="rem_sell") ) 
    bot.send_message(message.chat.id, "কি রিমুভ করতে চান?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rem_") or call.data.startswith("del_")) 
def handle_remove(call): 
    if call.from_user.id != ADMIN_ID: return
    if call.data.startswith("rem_"):
        mode = call.data.split("_")[1]
        markup = types.InlineKeyboardMarkup()
        source = items if mode == "shop" else sellable_types
        for n in source.keys():
            btn = types.InlineKeyboardButton(f"Remove {n}", callback_data=f"del_{mode}_{n}")
            markup.add(btn)
        bot.edit_message_text(f"{mode} থেকে কোনটি ডিলিট করবেন?", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif call.data.startswith("del_"):
        parts = call.data.split("_")
        mode = parts[1]
        name = "_".join(parts[2:]) 
        if mode == "shop" and name in items: 
            del items[name]
            save_data()
            bot.edit_message_text(f"✅ Shop থেকে '{name}' মুছে ফেলা হয়েছে।", call.message.chat.id, call.message.message_id)
        elif mode == "sell" and name in sellable_types: 
            del sellable_types[name]
            save_data()
            bot.edit_message_text(f"✅ Sellable থেকে '{name}' মুছে ফেলা হয়েছে।", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ আইটেমটি পাওয়া যায়নি।")

# --- BUY & SELL FLOW ---

@bot.message_handler(func=lambda m: m.text == "Shop") 
def shop(message): 
    if not items: bot.send_message(message.chat.id, "❌ শপ বর্তমানে খালি।"); return 
    markup = types.InlineKeyboardMarkup() 
    for n, d in items.items(): 
        if d['stock'] > 0: markup.add(types.InlineKeyboardButton(f"{n} ({d['price']} BDT)", callback_data=f"buy_{n}")) 
    bot.send_message(message.chat.id, "পণ্য কিনুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_")) 
def buy_item(call): 
    name = call.data.split("_", 1)[1] 
    item = items.get(name) 
    if not item: return 
    uid = call.from_user.id 
    if user_balances.get(uid, 0) < item['price']: bot.answer_callback_query(call.id, "❌ ব্যালেন্স কম!"); return 
    if item['stock'] <= 0: bot.answer_callback_query(call.id, "❌ স্টক শেষ!"); return
    user_balances[uid] -= item['price']
    item['stock'] -= 1
    save_data()
    if item['type'] == 'photo': bot.send_photo(uid, item['f_id'], caption=f"✅ কেনা সম্পন্ন: {name}")
    elif item['type'] == 'video': bot.send_video(uid, item['f_id'], caption=f"✅ কেনা সম্পন্ন: {name}")
    elif item['type'] == 'document': bot.send_document(uid, item['f_id'], caption=f"✅ কেনা সম্পন্ন: {name}")
    else: bot.send_message(uid, f"✅ কেনা সম্পন্ন: {name}\nকনটেন্ট: {item['text']}")
    bot.answer_callback_query(call.id, "✅ কেনা হয়েছে!")

@bot.message_handler(func=lambda m: m.text == "Sell") 
def show_sell(message): 
    if not sellable_types: bot.send_message(message.chat.id, "❌ কোনো আইটেম বিক্রির উপযোগী নেই।"); return 
    markup = types.InlineKeyboardMarkup() 
    for n, d in sellable_types.items(): markup.add(types.InlineKeyboardButton(f"{n} ({d['price']} BDT)", callback_data=f"sell_{n}"))
    bot.send_message(message.chat.id, "কী বিক্রি করবেন?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("sell_")) 
def finalize_sell(call): 
    name = call.data.split("_", 1)[1]
    pending_sells[call.from_user.id] = {"name": name} 
    msg = bot.send_message(call.from_user.id, "কত পিস সেল করবেন?")
    bot.register_next_step_handler(msg, get_quantity)

def get_quantity(message): 
    try: 
        qty = int(message.text)
        pending_sells[message.chat.id]["qty"] = qty 
        msg = bot.send_message(message.chat.id, "ফাইল বা টেক্সট পাঠান:")
        bot.register_next_step_handler(msg, save_sell) 
    except: bot.reply_to(message, "❌ শুধুমাত্র সংখ্যা লিখুন।")

def save_sell(message): 
    uid = message.chat.id 
    username = message.from_user.username or "NoUsername" 
    data = pending_sells[uid]
    f_id = message.photo[-1].file_id if message.photo else message.video.file_id if message.video else message.document.file_id if message.document else None
    f_type = 'photo' if message.photo else 'video' if message.video else 'document' if message.document else 'text'
    text = message.caption or message.text or "No content"
    pending_sells[uid].update({"f_id": f_id, "type": f_type, "text": text, "username": username})
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Approve", callback_data=f"appsell_{uid}"),
        types.InlineKeyboardButton("Deny", callback_data=f"denysell_{uid}")
    )
    msg_text = (f"🔔 নতুন সেল রিকোয়েস্ট!\n\nUser: @{username}\nID: {uid}\nItem: {data['name']}\nQty: {data['qty']}")
    bot.send_message(ADMIN_ID, msg_text, reply_markup=markup)
    bot.reply_to(message, "✅ আপনার সেল রিকোয়েস্টটি অ্যাডমিনের কাছে পাঠানো হয়েছে।")

@bot.callback_query_handler(func=lambda call: call.data.startswith(("appsell_", "denysell_"))) 
def handle_sell_approval(call): 
    if call.from_user.id != ADMIN_ID: return 
    action, uid = call.data.split("_") 
    uid = int(uid) 
    if action == "appsell":
        data = pending_sells[uid]
        name = data["name"] 
        qty = data["qty"] 
        price = sellable_types[name]['price'] 
        items[f"{name}{uid}"] = {"price": price, "stock": qty, "f_id": data["f_id"], "type": data["type"], "text": data["text"]}
        user_balances[uid] = user_balances.get(uid, 0) + (price * qty)
        save_data()
        bot.send_message(uid, f"✅ আপনার সেল রিকোয়েস্ট এপ্রুভ হয়েছে!")
        bot.edit_message_text(f"✅ এপ্রুভড! ইউজার: @{data['username']}", call.message.chat.id, call.message.message_id)
    else: 
        bot.send_message(uid, "❌ আপনার সেল রিকোয়েস্টটি রিজেক্ট করা হয়েছে।") 
        bot.edit_message_text(f"❌ ডেনিড! ইউজার: @{pending_sells.get(uid, {}).get('username', 'Unknown')}", call.message.chat.id, call.message.message_id) 
    if uid in pending_sells: del pending_sells[uid]

@bot.message_handler(commands=['start']) 
def start(message): 
    users_db[message.chat.id] = message.from_user.username or "NoUsername"
    save_data()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True); 
    markup.add("Shop", "Sell", "Balance", "Deposit", "Withdraw", "Contact Admin") 
    bot.send_message(message.chat.id, "👋 Shop v1.0 বটে আপনাকে স্বাগতম", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Balance") 
def bal(message):
    bot.send_message(message.chat.id, f"💰 ব্যালেন্স: {user_balances.get(message.chat.id, 0)} BDT")

@bot.message_handler(func=lambda m: m.text == "Deposit") 
def ask_amount(message): 
    bot.send_message(message.chat.id, f"বিকাশ করুন এই নাম্বারে: {deposit_number}\nকত টাকা ডিপোজিট করবেন?", parse_mode="Markdown")
    bot.register_next_step_handler(message, process_amount)

def process_amount(message): 
    deposit_requests[message.chat.id] = {"amount": message.text} 
    msg = bot.send_message(message.chat.id, "ট্রানজেকশন আইডি দিন:")
    bot.register_next_step_handler(msg, finalize_deposit)

def finalize_deposit(message): 
    uid = message.chat.id 
    markup = types.InlineKeyboardMarkup(); 
    markup.add(types.InlineKeyboardButton("Approve", callback_data=f"app_{uid}"), types.InlineKeyboardButton("Deny", callback_data=f"deny_{uid}")) 
    bot.send_message(ADMIN_ID, f"🔔 ডিপোজিট: {deposit_requests[uid]['amount']} BDT\nUser: @{message.from_user.username}\nTrx: {message.text}", reply_markup=markup) 
    bot.reply_to(message, "✅ অ্যাডমিনের কাছে পাঠানো হয়েছে।")

@bot.callback_query_handler(func=lambda call: call.data.startswith(("app_", "deny_"))) 
def callback_handler(call): 
    if call.from_user.id != ADMIN_ID: return 
    action, uid = call.data.split("_") 
    if action == "app": 
        user_balances[int(uid)] = user_balances.get(int(uid), 0) + int(deposit_requests[int(uid)]['amount'])
        save_data()
        bot.send_message(int(uid), "✅ এপ্রুভ হয়েছে!"); del deposit_requests[int(uid)]
    else: 
        bot.send_message(int(uid), "❌ রিজেক্ট হয়েছে!"); del deposit_requests[int(uid)] 
    bot.edit_message_text("✅ Done", call.message.chat.id, call.message.message_id)

# --- WITHDRAW LOGIC ---

@bot.message_handler(func=lambda m: m.text == "Withdraw")
def request_withdraw(message):
    uid = message.chat.id
    if user_balances.get(uid, 0) < 50:
        bot.send_message(uid, "❌ আপনার ব্যালেন্স পর্যাপ্ত নয়। সর্বনিম্ন ৫০ টাকা হতে হবে।")
        return
    msg = bot.send_message(uid, "আপনার বিকাশ নাম্বারটি দিন:")
    bot.register_next_step_handler(msg, get_withdraw_amount)

def get_withdraw_amount(message):
    uid = message.chat.id
    withdraw_requests[uid] = {"bkash": message.text}
    msg = bot.send_message(uid, "কত টাকা তুলতে চান?")
    bot.register_next_step_handler(msg, finalize_withdraw)

def finalize_withdraw(message):
    uid = message.chat.id
    try:
        amount = int(message.text)
        if amount > user_balances.get(uid, 0):
            bot.reply_to(message, "❌ আপনার ব্যালেন্স কম।")
            return
        withdraw_requests[uid]["amount"] = amount
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Approve", callback_data=f"appw_{uid}"), types.InlineKeyboardButton("Deny", callback_data=f"denyw_{uid}"))
        bot.send_message(ADMIN_ID, f"🔔 নতুন উইথড্র রিকোয়েস্ট!\n\nUser: @{message.from_user.username}\nID: {uid}\nNumber: {withdraw_requests[uid]['bkash']}\nAmount: {amount} BDT", reply_markup=markup)
        bot.reply_to(message, "✅ আপনার উইথড্র রিকোয়েস্টটি অ্যাডমিনের কাছে পাঠানো হয়েছে।")
    except: bot.reply_to(message, "❌ ভুল ফরম্যাট! শুধু সংখ্যা লিখুন।")

@bot.callback_query_handler(func=lambda call: call.data.startswith(("appw_", "denyw_")))
def handle_withdraw_approval(call):
    if call.from_user.id != ADMIN_ID: return
    action, uid = call.data.split("_")
    uid = int(uid)
    if action == "appw":
        amount = withdraw_requests[uid]['amount']
        user_balances[uid] -= amount
        save_data()
        bot.send_message(uid, f"✅ আপনার {amount} BDT উইথড্র রিকোয়েস্ট এপ্রুভ হয়েছে!")
        bot.edit_message_text(f"✅ এপ্রুভড! ইউজার: {uid}", call.message.chat.id, call.message.message_id)
    else:
        bot.send_message(uid, "❌ আপনার উইথড্র রিকোয়েস্টটি রিজেক্ট করা হয়েছে।")
        bot.edit_message_text(f"❌ ডেনিড! ইউজার: {uid}", call.message.chat.id, call.message.message_id)
    if uid in withdraw_requests: del withdraw_requests[uid]
# --- ADMIN PANEL & BROADCAST ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Broadcast", callback_data="admin_broadcast"),
               types.InlineKeyboardButton("View Users", callback_data="admin_view_users"))
    bot.send_message(message.chat.id, "Admin Panel:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in["admin_broadcast", "admin_view_users"])
def handle_admin_panel(call):
    if call.from_user.id != ADMIN_ID: return
    if call.data == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "সবার কাছে পাঠানোর মেসেজটি লিখুন:")
        bot.register_next_step_handler(msg, perform_broadcast)
    elif call.data == "admin_view_users":
        text = "👥 ইউজার লিস্ট:\n\n"
        for uid, uname in users_db.items():
            text += f"ID: {uid} | Username: @{uname}\n"
        bot.send_message(call.message.chat.id, text)

def perform_broadcast(message):
    for uid in users_db:
        try: bot.send_message(uid, f"📢 অ্যাডমিন বার্তা:\n\n{message.text}")
        except: continue
    bot.reply_to(message, "✅ সবার কাছে মেসেজ পাঠানো হয়েছে।")

# --- CONTACT ADMIN & REPLY ---
@bot.message_handler(func=lambda m: m.text == "Contact Admin")
def contact_admin(message):
    msg = bot.send_message(message.chat.id, "আপনার মেসেজটি লিখুন, অ্যাডমিন রিপ্লাই দিবে:")
    bot.register_next_step_handler(msg, forward_to_admin)

def forward_to_admin(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Reply", callback_data=f"reply_{message.chat.id}"))
    bot.send_message(ADMIN_ID, f"📩 নতুন মেসেজ:\n\nUser: @{message.from_user.username}\nID: {message.chat.id}\n\nMsg: {message.text}", reply_markup=markup)
    bot.reply_to(message, "✅ মেসেজটি অ্যাডমিনের কাছে পাঠানো হয়েছে।")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_"))
def admin_reply(call):
    uid = call.data.split("_")[1]
    msg = bot.send_message(ADMIN_ID, "ইউজারকে কী রিপ্লাই দিবেন?")
    bot.register_next_step_handler(msg, lambda m: bot.send_message(uid, f"🛡 অ্যাডমিন থেকে রিপ্লাই:\n\n{m.text}"))
if __name__ == "__main__": 
    threading.Thread(target=run_flask).start()
    
    # বট চালু হওয়ার সাথে সাথে ডাটা চেক করবে/পাঠাবে
    save_data() 
    
    # পোলিং স্টার্ট
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Polling error: {e}")
            import time
            time.sleep(5)
