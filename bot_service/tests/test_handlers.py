import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest
from jose import jwt

os.environ.setdefault("APP_NAME", "bot-service-test")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test_bot_token")
os.environ.setdefault("JWT_SECRET", "test_secret")
os.environ.setdefault("JWT_ALG", "HS256")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
os.environ.setdefault("OPENROUTER_API_KEY", "test_openrouter_key")
os.environ.setdefault("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
os.environ.setdefault("OPENROUTER_MODEL", "openrouter/free")
os.environ.setdefault("OPENROUTER_SITE_URL", "https://example.com")
os.environ.setdefault("OPENROUTER_APP_NAME", "bot-service-test")

from app.bot import handlers  # noqa: E402
from app.core.config import settings  # noqa: E402


class FakeUser:
    id = 123


class FakeChat:
    id = 456


class FakeMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.from_user = FakeUser()
        self.chat = FakeChat()
        self.message_id = 10
        self.answer = AsyncMock()


def create_test_token() -> str:
    now = datetime.now(UTC)

    payload = {
        "sub": "1",
        "role": "user",
        "iat": int(now.timestamp()),
        "exp": now + timedelta(minutes=60),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_alg,
    )


@pytest.mark.asyncio
async def test_token_handler_saves_token_to_redis(mocker) -> None:
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    mocker.patch("app.bot.handlers.get_redis", return_value=fake_redis)

    token = create_test_token()
    message = FakeMessage(text=f"/token {token}")
    command = SimpleNamespace(args=token)

    await handlers.token_handler(message, command)

    saved_token = await fake_redis.get("token:123")

    assert saved_token == token
    message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_text_handler_without_token_does_not_call_celery(mocker) -> None:
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    mocker.patch("app.bot.handlers.get_redis", return_value=fake_redis)
    delay_mock = mocker.patch("app.bot.handlers.llm_request.delay")

    message = FakeMessage(text="Привет")

    await handlers.text_handler(message)

    delay_mock.assert_not_called()
    message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_text_handler_with_token_calls_celery(mocker) -> None:
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    mocker.patch("app.bot.handlers.get_redis", return_value=fake_redis)
    delay_mock = mocker.patch("app.bot.handlers.llm_request.delay")

    token = create_test_token()
    await fake_redis.set("token:123", token)

    message = FakeMessage(text="Напиши годы жизни Льва Толстого")

    await handlers.text_handler(message)

    delay_mock.assert_called_once_with(
        456,
        "Напиши годы жизни Льва Толстого",
    )
    message.answer.assert_called_once()
