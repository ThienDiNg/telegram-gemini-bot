import os
import time
from types import SimpleNamespace

import pytest

# Sử dụng thông tin giả để import bot.
# Không cần API Key hoặc Telegram Token thật.
os.environ["TELEGRAM_TOKEN"] = "123456:TEST_TOKEN"
os.environ["GEMINI_API_KEY"] = "test-key"
os.environ["BOT_USERNAME"] = "test_bot"
os.environ["RENDER_EXTERNAL_URL"] = ""

import bot


@pytest.fixture(autouse=True)
def reset_bot_state(monkeypatch):
    """Đặt lại trạng thái trước mỗi bài test."""
    monkeypatch.setattr(
        bot,
        "GEMINI_MODELS",
        ["model-a", "model-b", "model-c"]
    )

    monkeypatch.setattr(bot, "_counter", 0)
    bot._cooldown_until.clear()

    yield

    bot._cooldown_until.clear()


def test_next_models_skips_cooling_down_models():
    """Không sử dụng model vẫn còn cooldown."""
    bot._cooldown_until["model-a"] = time.monotonic() + 300

    models = bot._next_models()

    assert models == ["model-b", "model-c"]


def test_next_models_rotates_order():
    """Các lượt gọi tiếp theo phải xoay tua thứ tự model."""
    first = bot._next_models()
    second = bot._next_models()

    assert first == ["model-a", "model-b", "model-c"]
    assert second == ["model-b", "model-c", "model-a"]


def test_expired_model_becomes_available():
    """Model hết cooldown phải được sử dụng trở lại."""
    bot._cooldown_until["model-a"] = time.monotonic() - 1
    bot._cooldown_until["model-b"] = time.monotonic() + 300
    bot._cooldown_until["model-c"] = time.monotonic() + 300

    models = bot._next_models()

    assert models == ["model-a"]


def test_all_models_cooling_down_does_not_call_gemini(monkeypatch):
    """Không gọi Gemini API nếu tất cả model đang cooldown."""
    for model in bot.GEMINI_MODELS:
        bot._cooldown_until[model] = time.monotonic() + 300

    calls = []

    def fake_generate_content(**kwargs):
        calls.append(kwargs["model"])
        raise Exception("429 quota exceeded")

    monkeypatch.setattr(
        bot,
        "client",
        SimpleNamespace(
            models=SimpleNamespace(
                generate_content=fake_generate_content
            )
        )
    )

    with pytest.raises(bot.AllModelsCoolingDown) as exc_info:
        bot.ask_gemini("Hello")

    assert calls == []

    assert 0 < exc_info.value.retry_after <= 300


def test_rotation_after_quota_error(monkeypatch):
    """Nếu model đầu gặp 429, bot phải thử model tiếp theo."""
    calls = []

    class FakeAPIError(Exception):
        code = 429

    def fake_generate_content(model, contents):
        calls.append(model)

        if model == "model-a":
            raise FakeAPIError("Quota exceeded")

        return SimpleNamespace(text="Test successful")

    monkeypatch.setattr(
        bot,
        "client",
        SimpleNamespace(
            models=SimpleNamespace(
                generate_content=fake_generate_content
            )
        )
    )

    result = bot.ask_gemini("Hello")

    assert result == "Test successful"
    assert calls == ["model-a", "model-b"]
    assert bot._cooldown_until["model-a"] > time.monotonic()

@pytest.mark.parametrize(
    "seconds, expected",
    [
        (1, "1 giây"),
        (1.0001, "2 giây"),
        (30, "30 giây"),
        (60, "1 phút"),
        (60.0001, "1 phút 1 giây"),
        (90, "1 phút 30 giây"),
        (3600, "1 giờ"),
        (5400, "1 giờ 30 phút"),
    ],
)
def test_format_wait(seconds, expected):
    """Định dạng thời gian chờ chính xác."""
    assert bot._format_wait(seconds) == expected
