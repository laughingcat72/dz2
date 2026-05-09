from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from app.core.jwt import decode_and_validate
from app.infra.redis import get_redis
from app.tasks.llm_tasks import llm_request

router = Router()


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    await message.answer(
        "Привет. Сначала отправь JWT-токен командой:\n"
        "/token <jwt>\n\n"
        "После этого можно отправлять вопросы к LLM."
    )


@router.message(Command("token"))
async def token_handler(message: Message, command: CommandObject) -> None:
    if command.args is None:
        await message.answer("Передай токен в формате: /token <jwt>")
        return

    token = command.args.strip()

    try:
        payload = decode_and_validate(token)
    except ValueError:
        await message.answer("Токен неверный или истёк.")
        return

    redis = get_redis()
    key = f"token:{message.from_user.id}"

    await redis.set(key, token)

    await message.answer(
        f"Токен принят и сохранён. User ID из JWT: {payload['sub']}"
    )


@router.message()
async def text_handler(message: Message) -> None:
    redis = get_redis()
    key = f"token:{message.from_user.id}"

    token = await redis.get(key)

    if token is None:
        await message.answer(
            "Нет сохранённого JWT-токена. Сначала отправь: /token <jwt>"
        )
        return

    try:
        decode_and_validate(token)
    except ValueError:
        await message.answer(
            "Сохранённый токен неверный или истёк. Отправь новый: /token <jwt>"
        )
        return

    if message.text is None:
        await message.answer("Отправь текстовый вопрос.")
        return

    llm_request.delay(
        message.chat.id,
        message.text,
    )

    await message.answer("Запрос принят. Ответ придёт через несколько часов.")
