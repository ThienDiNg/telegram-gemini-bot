import os
import time
import math
import threading
import traceback
import secrets
import telebot
from flask import Flask, request
from google import genai

TOKEN = (os.environ.get("TELEGRAM_TOKEN") or "").strip()
WEBHOOK_SECRET = (
    os.environ.get("TELEGRAM_WEBHOOK_SECRET") or ""
).strip()
GEMINI_API_KEY = (os.environ.get("GEMINI_API_KEY") or "").strip()
BOT_USERNAME = (os.environ.get("BOT_USERNAME") or "").strip().lstrip("@").lower()
RENDER_EXTERNAL_URL = (os.environ.get("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")

# Danh sách model xoay tua, cách nhau bằng dấu phẩy
GEMINI_MODELS = [
    m.strip()
    for m in os.environ.get(
        "GEMINI_MODELS",
        "gemini-3.8-flash,gemini-3.6-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite",
    ).split(",")
    if m.strip()
]
# Thời gian (giây) model bị cho nghỉ sau khi hết quota / lỗi
COOLDOWN_QUOTA = int(os.environ.get("COOLDOWN_QUOTA", "1800"))   # 429: 30 phút
COOLDOWN_MISSING = int(os.environ.get("COOLDOWN_MISSING", "21600"))  # 404: 6 giờ
COOLDOWN_BUSY = int(os.environ.get("COOLDOWN_BUSY", "60"))       # 500/503: 1 phút

bot = telebot.TeleBot(TOKEN, threaded=False)
client = genai.Client(api_key=GEMINI_API_KEY)
app = Flask(__name__)

_lock = threading.Lock()
_counter = 0
_cooldown_until = {}  # model -> thời điểm được dùng lại


class AllModelsFailed(Exception):
    pass


class AllModelsCoolingDown(Exception):
    def __init__(self, retry_after):
        self.retry_after = retry_after
        super().__init__(
            f"All models are cooling down. Retry after {retry_after:.1f} seconds."
        )


def _error_code(e):
    code = getattr(e, "code", None)
    if isinstance(code, int):
        return code
    s = str(e)
    for c in (429, 404, 503, 500):
        if str(c) in s[:20]:
            return c
    return None


def _next_models():
    """Trả về danh sách model khả dụng theo thứ tự xoay tua."""
    global _counter

    with _lock:
        now = time.monotonic()

        start = _counter % len(GEMINI_MODELS)
        _counter += 1

        ordered = GEMINI_MODELS[start:] + GEMINI_MODELS[:start]

        available = [
            model
            for model in ordered
            if _cooldown_until.get(model, 0) <= now
        ]

        if not available:
            retry_after = min(
                _cooldown_until.get(model, now) - now
                for model in GEMINI_MODELS
            )
            raise AllModelsCoolingDown(max(0, retry_after))

        return available


def _put_to_rest(model, seconds):
    with _lock:
        _cooldown_until[model] = time.monotonic() + seconds


def _format_wait(seconds):
    seconds = max(1, math.ceil(seconds))

    if seconds < 60:
        return f"{seconds} giây"

    minutes, remaining_seconds = divmod(seconds, 60)

    if minutes < 60:
        if remaining_seconds:
            return f"{minutes} phút {remaining_seconds} giây"
        return f"{minutes} phút"

    hours, remaining_minutes = divmod(minutes, 60)

    if remaining_minutes:
        return f"{hours} giờ {remaining_minutes} phút"

    return f"{hours} giờ"


def ask_gemini(prompt):
    last_error = None

    for model in _next_models():
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt
            )

            answer = response.text or "Mình chưa có câu trả lời cho việc này."
            print(f"[OK] model={model}")
            return answer

        except Exception as e:
            last_error = e
            code = _error_code(e)

            if code == 429:
                _put_to_rest(model, COOLDOWN_QUOTA)

            elif code == 404:
                _put_to_rest(model, COOLDOWN_MISSING)

            elif code in (500, 503):
                _put_to_rest(model, COOLDOWN_BUSY)

            else:
                raise

            print(
                f"[SKIP] model={model} code={code}, "
                "thử model kế tiếp"
            )

    raise AllModelsFailed(str(last_error))


@app.route("/webhook", methods=["POST"])
def webhook():
    received_secret = request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token", ""
    )

    if (
        not WEBHOOK_SECRET
        or not secrets.compare_digest(received_secret, WEBHOOK_SECRET)
    ):
        return "Forbidden", 403

    try:
        update = telebot.types.Update.de_json(
            request.get_data().decode("utf-8")
        )
        bot.process_new_updates([update])
    except Exception:
        traceback.print_exc()

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
        is_mentioned = bool(BOT_USERNAME) and f"@{BOT_USERNAME}" in text.lower()
        if not (is_mentioned or is_reply_to_bot):
            return
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
        answer = ask_gemini(prompt_text)
        for i in range(0, len(answer), 4000):
            bot.reply_to(message, answer[i:i + 4000])
    except Exception as e:
        print("Lỗi:", repr(e))
        traceback.print_exc()

        if isinstance(e, AllModelsCoolingDown):
            wait_time = _format_wait(e.retry_after)
            msg = (
                f"⏳ Tất cả AI hiện đang bận hoặc hết lượt sử dụng.\n"
                f"Bạn vui lòng thử lại sau {wait_time} nhé."
            )

        elif isinstance(e, AllModelsFailed):
            msg = "⚠️ Các model AI hiện không khả dụng, bạn quay lại sau nhé."

        else:
            msg = "⚠️ Đã xảy ra lỗi khi gọi AI, bạn thử lại sau nhé."
        try:
            bot.reply_to(message, msg)
        except Exception:
            traceback.print_exc()


def register_webhook():
    if RENDER_EXTERNAL_URL and TOKEN and WEBHOOK_SECRET:
        try:
            bot.remove_webhook()
            bot.set_webhook(
                url=f"{RENDER_EXTERNAL_URL}/webhook",
                secret_token=WEBHOOK_SECRET,
            )
        except Exception:
            traceback.print_exc()

    elif RENDER_EXTERNAL_URL and TOKEN:
        print(
            "[ERROR] TELEGRAM_WEBHOOK_SECRET is missing. "
            "Webhook was not registered."
        )


register_webhook()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
