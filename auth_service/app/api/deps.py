from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidTokenError
from app.core.security import decode_token
from app.db.models import User
from app.db.session import AsyncSessionLocal
from app.repositories.users import UserRepository
from app.usecases.auth import AuthUseCase

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_users_repo(
    session: AsyncSession = Depends(get_db),
) -> UserRepository:
    return UserRepository(session)


async def get_auth_uc(
    users_repo: UserRepository = Depends(get_users_repo),
) -> AuthUseCase:
    return AuthUseCase(users_repo)


async def get_current_user_id(
    token: str = Depends(oauth2_scheme),
) -> int:
    payload = decode_token(token)
    user_id = payload.get("sub")

    if user_id is None:
        raise InvalidTokenError()

    try:
        return int(user_id)
    except ValueError as error:
        raise InvalidTokenError() from error


async def get_current_user(
    user_id: int = Depends(get_current_user_id),
    users_repo: UserRepository = Depends(get_users_repo),
) -> User:
    user = await users_repo.get_by_id(user_id)

    if user is None:
        raise InvalidTokenError()

    return user
