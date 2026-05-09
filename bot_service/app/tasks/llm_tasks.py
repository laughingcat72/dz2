import httpx

from app.core.config import settings
from app.infra.celery_app import celery_app
from app.services.openrouter_client import ask_openrouter


def send_telegram_message(chat_id: int, text: str) -> None:
    if not settings.telegram_bot_token:
        return

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    with httpx.Client(timeout=30.0) as client:
        client.post(url, json=payload)


@celery_app.task(name="app.tasks.llm_tasks.llm_request")
def llm_request(tg_chat_id: int, prompt: str) -> str:
    answer = ask_openrouter(prompt)

    send_telegram_message(
        chat_id=tg_chat_id,
        text=answer,
    )

    return answer
