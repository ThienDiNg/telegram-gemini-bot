import os
import telebot
from flask import Flask, request
from google import genai

TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BOT_USERNAME = (os.environ.get("BOT_USERNAME") or "").lstrip("@").lower()
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

bot = telebot.TeleBot(TOKEN, threaded=False)
client = genai.Client(api_key=GEMINI_API_KEY)
app = Flask(__name__)


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "!", 200


@app.route("/")
def index():
    return "🤖 Telegram Gemini Bot is running smoothly!", 200


@bot.message_handler(func=lambda m: True)
def handle_message(message):
    text = message.text or ""
    if not text:
        return

    if message.chat.type in ["group", "supergroup"]:
        reply = message.reply_to_message
        is_reply_to_bot = (
            reply is not None
            and reply.from_user is not None
            and (reply.from_user.username or "").lower() == BOT_USERNAME
        )
        is_mentioned = f"@{BOT_USERNAME}" in text.lower()
        if not (is_mentioned or is_reply_to_bot):
            return
        prompt_text = text.replace(f"@{BOT_USERNAME}", "").strip()
    else:
        prompt_text = text.strip()

    if not prompt_text:
        return

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_text,
        )
        answer = response.text or "Mình chưa có câu trả lời cho việc này."
        for i in range(0, len(answer), 4000):
            bot.reply_to(message, answer[i:i + 4000])
    except Exception as e:
        print("Lỗi:", e)
        bot.reply_to(message, f"⚠️ Đã xảy ra lỗi: {e}")


# Chạy cả khi dùng gunicorn
if RENDER_EXTERNAL_URL:
    bot.remove_webhook()
    bot.set_webhook(url=f"{RENDER_EXTERNAL_URL}/{TOKEN}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
