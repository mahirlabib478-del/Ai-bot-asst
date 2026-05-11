import telebot
import google.generativeai as genai  # Example using Gemini

# 1. Setup APIs
TOKEN = "8603882237:AAHmTymMc22waHTceuDAVqybw8Nyvej8_Eo"
ADMIN_ID = 8538304896
genai.configure(api_key="AIzaSyARtnv7YP6JSRKj52MK0DbiY77XPk2w9gE") # Add your AI key here

bot = telebot.TeleBot(TOKEN)
model = genai.GenerativeModel('gemini-pro')

# 2. The AI Handler
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    try:
        # Send user text to AI
        response = model.generate_content(message.text)
        # Reply to user with AI response
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, "Sorry, I encountered an error.")
        print(e)

# ... (rest of your existing Flask/threading code)
