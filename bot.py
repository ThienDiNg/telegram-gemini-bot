import os
import traceback
import telebot
from flask import Flask, request
from google import genai

TOKEN = (os.environ.get("TELEGRAM_TOKEN") or "").strip()
GEMINI_API_KEY = (os.environ.get("GEMINI_API_KEY") or "").strip()
BOT_USERNAME = (os.environ.get("BOT_USERNAME") or "").strip().lstrip("@").lower()
RENDER_EXTERNAL_URL = (os.environ.get("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

bot = telebot.TeleBot(TOKEN, threaded=False)
client = genai.Client(api_key=GEMINI_API_KEY)
app = Flask(__name__)


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
        bot.process_new_updates([update])
    except Exception:
        traceback.print_exc()  # xem chi tiết trong Logs của Render
    return "!", 200  # luôn trả 200 để Telegram không gửi lại tin cũ


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
        is_mentioned = bool(BOT_USERNAME) and f"@{BOT_USERNAME}" in text.lower()
        if not (is_mentioned or is_reply_to_bot):
            return
        # xoá mention không phân biệt hoa/thường
        prompt_text = text
        if is_mentioned:
            idx = text.lower().find(f"@{BOT_USERNAME}")
            prompt_text = (text[:idx] + text[idx + len(BOT_USERNAME) + 1:]).strip()
        else:
            prompt_text = text.strip()
    else:
        prompt_text = text.strip()

    if not prompt_text:
        return

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt_text,
        )
        answer = response.text or "Mình chưa có câu trả lời cho việc này."
        for i in range(0, len(answer), 4000):
            bot.reply_to(message, answer[i:i + 4000])
    except Exception as e:
        print("Lỗi:", repr(e))
        traceback.print_exc()
        try:
            bot.reply_to(message, "⚠️ Đã xảy ra lỗi khi gọi AI, bạn thử lại sau nhé.")
        except Exception:
            traceback.print_exc()


# Đăng ký webhook (chạy cả khi dùng gunicorn)
if RENDER_EXTERNAL_URL and TOKEN:
    try:
        bot.remove_webhook()
        bot.set_webhook(url=f"{RENDER_EXTERNAL_URL}/{TOKEN}")
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
