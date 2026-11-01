import os
import telebot
from flask import Flask, request
from google import genai

# Lấy thông tin cấu hình từ biến môi trường của Render
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BOT_USERNAME = os.environ.get("BOT_USERNAME")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

bot = telebot.TeleBot(TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)
app = Flask(__name__)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    """Nhận tin nhắn từ Telegram đẩy sang"""
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def index():
    return "🤖 Telegram Gemini Bot is running smoothly!", 200

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    is_group = message.chat.type in ['group', 'supergroup']
    
    if is_group:
        is_reply_to_bot = (
            message.reply_to_message is not None and 
            message.reply_to_message.from_user.username == BOT_USERNAME
        )
        is_mentioned = f"@{BOT_USERNAME}" in (message.text or "")

        if not (is_mentioned or is_reply_to_bot):
            return

        prompt_text = message.text.replace(f"@{BOT_USERNAME}", "").strip()
    else:
        prompt_text = message.text

    if not prompt_text:
        return

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt_text,
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Đã xảy ra lỗi: {e}")

if __name__ == "__main__":
    # Tự động cấu hình Webhook khi Render khởi chạy
    if RENDER_EXTERNAL_URL:
        bot.remove_webhook()
        bot.set_webhook(url=f"{RENDER_EXTERNAL_URL}/{TOKEN}")
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
