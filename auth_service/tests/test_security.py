import os

os.environ.setdefault("APP_NAME", "auth-service-test")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("JWT_SECRET", "test_secret")
os.environ.setdefault("JWT_ALG", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("SQLITE_PATH", "./test_auth.db")

from app.core.security import (  # noqa: E402
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_and_verify_password() -> None:
    password = "123456"

    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash) is True
    assert verify_password("wrong_password", password_hash) is False


def test_create_and_decode_access_token() -> None:
    token = create_access_token(
        user_id=1,
        role="user",
    )

    payload = decode_token(token)

    assert payload["sub"] == "1"
    assert payload["role"] == "user"
    assert "iat" in payload
    assert "exp" in payload
