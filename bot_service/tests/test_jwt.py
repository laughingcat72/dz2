import os
from datetime import UTC, datetime, timedelta

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

from app.core.config import settings  # noqa: E402
from app.core.jwt import decode_and_validate  # noqa: E402


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


def test_decode_and_validate_valid_token() -> None:
    token = create_test_token()

    payload = decode_and_validate(token)

    assert payload["sub"] == "1"
    assert payload["role"] == "user"
    assert "iat" in payload
    assert "exp" in payload


def test_decode_and_validate_invalid_token() -> None:
    with pytest.raises(ValueError):
        decode_and_validate("invalid.token.value")
