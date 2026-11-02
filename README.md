# 🤖 Telegram Gemini Bot

Bot Telegram trả lời bằng AI của Google Gemini. Viết bằng Python (Flask + pyTelegramBotAPI), nhận tin nhắn qua webhook và triển khai trên [Render](https://render.com). Hỗ trợ **xoay tua nhiều model Gemini** để chia đều hạn mức miễn phí và tự chuyển model khi gặp lỗi.

## ✨ Tính năng

- Chat riêng: nhắn trực tiếp, bot trả lời bằng Gemini.
- Trong nhóm: chỉ trả lời khi được **tag @tên_bot** hoặc khi ai đó **reply tin nhắn của bot**.
- **Xoay tua model (round-robin):** mỗi tin nhắn bắt đầu từ một model khác nhau để chia đều lượt dùng.
- **Tự động chuyển model khi lỗi:** hết quota (429), model không tồn tại (404) hoặc quá tải (500/503) thì bot chuyển ngay sang model kế tiếp.
- **Cooldown thông minh:** model lỗi được cho nghỉ một thời gian rồi tự quay lại.
- Tự chia nhỏ câu trả lời dài (giới hạn 4096 ký tự của Telegram).
- Tự đăng ký webhook khi khởi động.
- Ghi log rõ ràng: `[OK]` model đã trả lời, `[SKIP]` model bị bỏ qua.

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

### Bắt buộc

| Biến | Mô tả |
|------|-------|
| `TELEGRAM_TOKEN` | Token bot từ @BotFather |
| `GEMINI_API_KEY` | API key của Google Gemini |
| `BOT_USERNAME` | Username của bot, **không** có dấu `@` |
| `RENDER_EXTERNAL_URL` | URL công khai của service, ví dụ `https://ten-app.onrender.com` (Render thường tự cấp) |

### Tuỳ chọn

| Biến | Mô tả | Mặc định |
|------|-------|----------|
| `GEMINI_MODELS` | Danh sách model xoay tua, cách nhau bằng dấu phẩy | `gemini-3.8-flash,gemini-3.6-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite` |
| `COOLDOWN_QUOTA` | Số giây model nghỉ sau khi hết quota (429) | `1800` |
| `COOLDOWN_MISSING` | Số giây model nghỉ khi không tồn tại (404) | `21600` |
| `COOLDOWN_BUSY` | Số giây model nghỉ khi quá tải (500/503) | `60` |
| `PORT` | Cổng chạy server, Render tự cấp | `5000` |

Ví dụ muốn chỉ dùng một model duy nhất:

```
GEMINI_MODELS=gemini-3.8-flash
```

## 🔄 Cách xoay tua model hoạt động

1. Mỗi tin nhắn bắt đầu từ một model khác nhau trong `GEMINI_MODELS` theo vòng tròn.
2. Nếu model trả về lỗi 429 / 404 / 500 / 503, bot cho model đó nghỉ (cooldown) rồi thử model kế tiếp.
3. Các lỗi khác (ví dụ API key sai) không xoay tua mà báo lỗi ngay.
4. Nếu tất cả model đều lỗi, bot gửi thông báo thân thiện cho người dùng.

> Hạn mức miễn phí của Gemini được tính **riêng cho từng model**, nên xoay tua giúp kéo dài số lượt dùng mỗi ngày. Trạng thái cooldown lưu trong bộ nhớ nên sẽ được đặt lại khi service khởi động lại.

Danh sách model hiện hành xem tại [tài liệu Gemini API](https://ai.google.dev/gemini-api/docs/models). Hạn mức từng model xem tại [AI Studio Rate Limit](https://ai.dev/rate-limit).

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

**Webhook báo `500 Internal Server Error`**
- Lỗi xảy ra trong code. Xem Logs để biết dòng lỗi cụ thể.

**Webhook báo `SSL error ... handshake failure`**
- Thường do service Render đang "ngủ". Mở URL của service trên trình duyệt để đánh thức, rồi đặt lại webhook kèm xoá tin kẹt:
  `https://api.telegram.org/bot<TOKEN>/setWebhook?url=<URL>/<TOKEN>&drop_pending_updates=true`

**Bot không đọc tin nhắn trong nhóm**
- Kiểm tra `BOT_USERNAME` đúng với username bot (không có `@`).
- Tắt Privacy Mode: @BotFather → `/setprivacy` → chọn bot → **Disable**, sau đó **kick bot khỏi nhóm rồi add lại**.
- Trong nhóm phải tag `@tên_bot` hoặc reply tin nhắn của bot.

**Lỗi `429 RESOURCE_EXHAUSTED`**
- Model đã hết hạn mức miễn phí trong ngày. Bot sẽ tự chuyển sang model khác. Để dùng ổn định hơn, thêm nhiều model vào `GEMINI_MODELS` hoặc bật billing cho project.

**Lỗi `404` (model không tồn tại)**
- Kiểm tra lại tên model trong `GEMINI_MODELS` so với [danh sách chính thức](https://ai.google.dev/gemini-api/docs/models).

**Bot phản hồi chậm ở lần đầu**
- Gói miễn phí của Render sẽ "ngủ" sau khoảng 15 phút không hoạt động. Có thể dùng dịch vụ ping định kỳ (như UptimeRobot) vào đường dẫn `/` để giữ bot luôn thức.

## 🔒 Bảo mật

- Không commit token hoặc API key lên GitHub, chỉ đặt trong biến môi trường.
- Nếu lỡ lộ token, dùng `/revoke` ở @BotFather để cấp token mới.

## 📄 Giấy phép

Bản quyền thuộc về tác giả, bảo lưu mọi quyền. Xem chi tiết trong file [LICENSE](LICENSE).
