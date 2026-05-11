import os
import telebot
import google.generativeai as genai
from flask import Flask, request

TOKEN = os.getenv("8603882237:AAHmTymMc22waHTceuDAVqybw8Nyvej8_Eo")
ADMIN_ID = 8538304896
API_KEY = os.getenv("AIzaSyARtnv7YP6JSRKj52MK0DbiY77XPk2w9gE")

bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-pro')

app = Flask(__name__)

@app.route(f'/{TOKEN}', methods=['POST'])
def get_message():
    json_str = request.stream.read().decode('utf-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/')
def home():
    return "Bot is running!"

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Hello! I am your AI Assistant.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        response = model.generate_content(message.text)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, "⚠️ Error.")

if __name__ == "__main__":
    # Set the webhook to your Render URL
    # Replace 'your-app-name' with your actual Render URL
    WEBHOOK_URL = f"https://your-app-name.onrender.com/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
