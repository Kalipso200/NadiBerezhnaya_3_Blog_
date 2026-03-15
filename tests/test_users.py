"""
Тесты для пользователей
"""
import pytest
from fastapi import status

def test_login_success(client, test_user):
    """Тест успешного входа"""
    # Подготовка данных
    json_data = {
        "username": "testuser",
        "password": "TestPass123"
    }

    # Отправка запроса с JSON
    response = client.post(
        "/token",
        json=json_data,  # Используем json, а не data!
        headers={"Content-Type": "application/json"}
    )

    # Отладка
    print(f"\nСтатус ответа: {response.status_code}")
    print(f"Заголовки ответа: {dict(response.headers)}")
    print(f"Тело ответа: {response.text}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0

def test_login_wrong_password(client, test_user):
    """Тест входа с неверным паролем"""
    response = client.post(
        "/token",
        json={
            "username": "testuser",
            "password": "WrongPass123"
        },
        headers={"Content-Type": "application/json"}
    )
    print(f"\nСтатус ответа: {response.status_code}")
    print(f"Тело ответа: {response.text}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_login_nonexistent_user(client):
    """Тест входа с несуществующим пользователем"""
    response = client.post(
        "/token",
        json={
            "username": "nonexistent",
            "password": "TestPass123"
        },
        headers={"Content-Type": "application/json"}
    )
    print(f"\nСтатус ответа: {response.status_code}")
    print(f"Тело ответа: {response.text}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_login_wrong_format(client, test_user):
    """Тест входа с неправильным форматом (form-data вместо JSON)"""
    response = client.post(
        "/token",
        data={  # Это должно вернуть 422
            "username": "testuser",
            "password": "TestPass123"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    print(f"\nСтатус ответа: {response.status_code}")
    print(f"Тело ответа: {response.text}")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY