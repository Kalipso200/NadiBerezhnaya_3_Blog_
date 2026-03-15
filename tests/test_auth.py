"""
Тесты для авторизации
"""
import pytest
from fastapi import status
from app.auth import create_access_token, verify_password, get_password_hash
from datetime import timedelta, datetime, timezone
from jose import jwt
from app.config import settings

def test_password_hashing():
    """Тест хеширования паролей"""
    password = "TestPass123"
    hashed = get_password_hash(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPass", hashed) is False

def test_password_hashing_long_password():
    """Тест хеширования длинного пароля"""
    long_password = "A" * 100 + "123"
    hashed = get_password_hash(long_password)
    assert verify_password(long_password, hashed) is True

def test_create_access_token():
    """Тест создания JWT токена"""
    data = {"sub": "testuser"}
    token = create_access_token(data)
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0

def test_create_access_token_with_expiry():
    """Тест создания токена с определенным сроком действия"""
    data = {"sub": "testuser"}
    expires = timedelta(minutes=5)
    token = create_access_token(data, expires_delta=expires)
    assert token is not None

    # Декодируем и проверяем срок
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert "exp" in payload

def test_token_with_different_data():
    """Тест токена с разными данными"""
    data1 = {"sub": "user1", "role": "admin"}
    data2 = {"sub": "user2", "role": "user"}

    token1 = create_access_token(data1)
    token2 = create_access_token(data2)

    assert token1 != token2

    # Проверяем что данные сохранились
    payload1 = jwt.decode(token1, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    payload2 = jwt.decode(token2, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert payload1["sub"] == "user1"
    assert payload1["role"] == "admin"
    assert payload2["sub"] == "user2"
    assert payload2["role"] == "user"

@pytest.mark.parametrize("auth_header,expected_status", [
    (None, status.HTTP_401_UNAUTHORIZED),
    ("", status.HTTP_401_UNAUTHORIZED),
    ("Bearer invalid.token", status.HTTP_401_UNAUTHORIZED),
    ("NotBearer token", status.HTTP_401_UNAUTHORIZED),
])
def test_auth_header_formats(client, auth_header, expected_status):
    """Тест различных форматов заголовка авторизации"""
    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header

    response = client.get("/users/me", headers=headers)
    assert response.status_code == expected_status

def test_auth_with_bearer_prefix(client, test_user_token):
    """Тест авторизации с правильным форматом Bearer"""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    response = client.get("/users/me", headers=headers)
    assert response.status_code == status.HTTP_200_OK

def test_auth_without_bearer_prefix(client, test_user_token):
    """Тест авторизации без префикса Bearer (не должно работать)"""
    headers = {"Authorization": test_user_token}
    response = client.get("/users/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_expired_token(client):
    """Тест истекшего токена"""
    # Создаем токен с истекшим сроком
    expired_data = {
        "sub": "testuser",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1)
    }

    expired_token = jwt.encode(expired_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/users/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Token has expired" in response.text