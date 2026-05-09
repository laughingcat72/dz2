import os

import respx
from httpx import Response

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

from app.services.openrouter_client import ask_openrouter  # noqa: E402


@respx.mock
def test_ask_openrouter_returns_answer() -> None:
    route = respx.post(
        "https://openrouter.ai/api/v1/chat/completions",
    ).mock(
        return_value=Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "Тестовый ответ от LLM",
                        },
                    },
                ],
            },
        ),
    )

    answer = ask_openrouter("Привет")

    assert answer == "Тестовый ответ от LLM"
    assert route.called
