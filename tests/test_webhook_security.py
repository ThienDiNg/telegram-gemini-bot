
import os
from unittest.mock import Mock

import pytest

# Sử dụng thông tin giả để import bot.
os.environ["TELEGRAM_TOKEN"] = "123456:TEST_TOKEN"
os.environ["TELEGRAM_WEBHOOK_SECRET"] = "test-webhook-secret"
os.environ["GEMINI_API_KEY"] = "test-key"
os.environ["BOT_USERNAME"] = "test_bot"
os.environ["RENDER_EXTERNAL_URL"] = ""

import bot


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        bot,
        "WEBHOOK_SECRET",
        "test-webhook-secret"
    )

    bot.app.config["TESTING"] = True

    with bot.app.test_client() as test_client:
        yield test_client


def test_webhook_rejects_missing_secret(client, monkeypatch):
    process_updates = Mock()
    monkeypatch.setattr(bot.bot, "process_new_updates", process_updates)

    response = client.post("/webhook")

    assert response.status_code == 403
    process_updates.assert_not_called()


def test_webhook_rejects_invalid_secret(client, monkeypatch):
    process_updates = Mock()
    monkeypatch.setattr(bot.bot, "process_new_updates", process_updates)

    response = client.post(
        "/webhook",
        headers={
            "X-Telegram-Bot-Api-Secret-Token": "wrong-secret"
        },
        json={},
    )

    assert response.status_code == 403
    process_updates.assert_not_called()


def test_webhook_accepts_valid_secret(client, monkeypatch):
    process_updates = Mock()
    monkeypatch.setattr(bot.bot, "process_new_updates", process_updates)

    response = client.post(
        "/webhook",
        headers={
            "X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"
        },
        json={"update_id": 123456},
    )

    assert response.status_code == 200
    process_updates.assert_called_once()



def test_register_webhook_uses_secret_token(monkeypatch):
    remove_webhook = Mock()
    set_webhook = Mock()

    monkeypatch.setattr(bot, "RENDER_EXTERNAL_URL", "https://example.onrender.com")
    monkeypatch.setattr(bot, "TOKEN", "test-token")
    monkeypatch.setattr(bot, "WEBHOOK_SECRET", "test-webhook-secret")
    monkeypatch.setattr(bot.bot, "remove_webhook", remove_webhook)
    monkeypatch.setattr(bot.bot, "set_webhook", set_webhook)

    bot.register_webhook()

    remove_webhook.assert_called_once()
    set_webhook.assert_called_once_with(
        url="https://example.onrender.com/webhook",
        secret_token="test-webhook-secret",
    )


def test_register_webhook_skips_when_secret_missing(monkeypatch, capsys):
    remove_webhook = Mock()
    set_webhook = Mock()

    monkeypatch.setattr(bot, "RENDER_EXTERNAL_URL", "https://example.onrender.com")
    monkeypatch.setattr(bot, "TOKEN", "test-token")
    monkeypatch.setattr(bot, "WEBHOOK_SECRET", "")
    monkeypatch.setattr(bot.bot, "remove_webhook", remove_webhook)
    monkeypatch.setattr(bot.bot, "set_webhook", set_webhook)

    bot.register_webhook()

    remove_webhook.assert_not_called()
    set_webhook.assert_not_called()

    assert "TELEGRAM_WEBHOOK_SECRET is missing" in capsys.readouterr().out
