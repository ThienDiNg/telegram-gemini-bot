# 🤖 Telegram Gemini Bot

Bot Telegram trả lời bằng AI của Google Gemini. Viết bằng Python (Flask + pyTelegramBotAPI), nhận tin nhắn qua webhook và triển khai trên [Render](https://render.com).

## ✨ Tính năng

- Chat riêng: nhắn trực tiếp, bot trả lời bằng Gemini.
- Trong nhóm: chỉ trả lời khi được **tag @tên_bot** hoặc khi ai đó **reply tin nhắn của bot**.
- Tự chia nhỏ câu trả lời dài (giới hạn 4096 ký tự của Telegram).
- Tự đăng ký webhook khi khởi động.
- Đổi model Gemini chỉ bằng biến môi trường, không cần sửa code.

## 📁 Cấu trúc dự án

```
.
├── bot.py             # Mã nguồn chính của bot
├── requirements.txt   # Danh sách thư viện
└── README.md
```

## 🔧 Yêu cầu

- Python 3.9 trở lên
- Token bot Telegram, lấy từ [@BotFather](https://t.me/BotFather)
- API key Gemini, lấy từ [Google AI Studio](https://aistudio.google.com/)

## ⚙️ Biến môi trường

| Biến | Bắt buộc | Mô tả |
|------|----------|-------|
| `TELEGRAM_TOKEN` | ✅ | Token bot từ @BotFather |
| `GEMINI_API_KEY` | ✅ | API key của Google Gemini |
| `BOT_USERNAME` | ✅ | Username của bot, **không** có dấu `@` |
| `RENDER_EXTERNAL_URL` | ✅ | URL công khai của service, ví dụ `https://ten-app.onrender.com` (Render thường tự cấp) |
| `GEMINI_MODEL` | ❌ | Tên model Gemini, mặc định `gemini-3.6-flash` |
| `PORT` | ❌ | Cổng chạy server, Render tự cấp |

## 🚀 Triển khai lên Render

1. Đưa mã nguồn lên GitHub.
2. Trên Render, chọn **New → Web Service** và kết nối repo.
3. Cấu hình:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn bot:app --bind 0.0.0.0:$PORT`
4. Thêm các biến môi trường ở tab **Environment** (xem bảng trên).
5. Deploy. Khi khởi động, bot sẽ tự đăng ký webhook với Telegram.

## 💻 Chạy thử trên máy

```bash
pip install -r requirements.txt

export TELEGRAM_TOKEN="your_telegram_token"
export GEMINI_API_KEY="your_gemini_key"
export BOT_USERNAME="your_bot_username"

python bot.py
```

> Chạy local cần một URL công khai (ví dụ dùng ngrok) để Telegram gửi webhook tới, sau đó đặt `RENDER_EXTERNAL_URL` bằng URL đó.

## 🛠️ Xử lý sự cố

**Bot không trả lời**
- Kiểm tra webhook: mở `https://api.telegram.org/bot<TOKEN>/getWebhookInfo`. Trường `url` phải đúng và không có `last_error_message`.
- Xem tab **Logs** trên Render, tìm dòng `Traceback`.

**Bot không đọc tin nhắn trong nhóm**
- Tắt Privacy Mode: @BotFather → `/setprivacy` → chọn bot → **Disable**.

**Lỗi model (404)**
- Model không còn tồn tại. Đặt `GEMINI_MODEL` sang model khác, ví dụ `gemini-2.5-flash`. Xem danh sách tại [tài liệu Gemini API](https://ai.google.dev/models).

**Bot phản hồi chậm ở lần đầu**
- Gói miễn phí của Render sẽ "ngủ" sau khoảng 15 phút không hoạt động. Có thể dùng dịch vụ ping định kỳ (như UptimeRobot) vào đường dẫn `/` để giữ bot luôn thức.

## 🔒 Bảo mật

- Không commit token hoặc API key lên GitHub, chỉ đặt trong biến môi trường.
- Nếu lỡ lộ token, dùng `/revoke` ở @BotFather để cấp token mới.
