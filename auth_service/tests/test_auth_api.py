import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("APP_NAME", "auth-service-test")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("JWT_SECRET", "test_secret")
os.environ.setdefault("JWT_ALG", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("SQLITE_PATH", "./test_auth.db")

from app.api.deps import get_db  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
async def client(tmp_path) -> AsyncGenerator[AsyncClient]:
    test_db_path = tmp_path / "test_auth.db"
    test_database_url = f"sqlite+aiosqlite:///{test_db_path}"

    test_engine = create_async_engine(test_database_url)
    test_session_maker = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
    )

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        async with test_session_maker() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_register_login_and_me(client: AsyncClient) -> None:
    register_response = await client.post(
        "/auth/register",
        json={
            "email": "surname@email.com",
            "password": "123456",
        },
    )

    assert register_response.status_code == 201
    register_data = register_response.json()
    assert register_data["email"] == "surname@email.com"
    assert register_data["role"] == "user"
    assert "password_hash" not in register_data

    login_response = await client.post(
        "/auth/login",
        data={
            "username": "surname@email.com",
            "password": "123456",
        },
    )

    assert login_response.status_code == 200
    login_data = login_response.json()
    assert login_data["token_type"] == "bearer"
    assert login_data["access_token"]

    token = login_data["access_token"]

    me_response = await client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == "surname@email.com"
    assert me_data["role"] == "user"


@pytest.mark.asyncio
async def test_duplicate_register_returns_409(client: AsyncClient) -> None:
    payload = {
        "email": "duplicate@email.com",
        "password": "123456",
    }

    first_response = await client.post(
        "/auth/register",
        json=payload,
    )
    second_response = await client.post(
        "/auth/register",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


@pytest.mark.asyncio
async def test_login_with_wrong_password_returns_401(client: AsyncClient) -> None:
    await client.post(
        "/auth/register",
        json={
            "email": "wrong-password@email.com",
            "password": "123456",
        },
    )

    login_response = await client.post(
        "/auth/login",
        data={
            "username": "wrong-password@email.com",
            "password": "wrong_password",
        },
    )

    assert login_response.status_code == 401


@pytest.mark.asyncio
async def test_me_without_token_returns_401(client: AsyncClient) -> None:
    response = await client.get("/auth/me")

    assert response.status_code == 401
