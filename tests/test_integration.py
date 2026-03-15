"""
Интеграционные тесты
"""
import pytest
from fastapi import status

def test_full_user_flow(client):
    """Полный цикл работы пользователя"""
    # 1. Регистрация
    register_data = {
        "username": "integration_user",
        "email": "integration@example.com",
        "password": "IntegrationPass123"
    }
    response = client.post("/register", json=register_data)
    assert response.status_code == status.HTTP_201_CREATED

    # 2. Вход (правильный формат - JSON!)
    response = client.post(
        "/token",
        json={  # ВАЖНО: используем json, а не data!
            "username": "integration_user",
            "password": "IntegrationPass123"
        }
    )
    assert response.status_code == status.HTTP_200_OK, f"Ошибка: {response.text}"
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Создание поста
    post_data = {
        "title": "Integration Post",
        "content": "Integration Content"
    }
    response = client.post("/posts/", json=post_data, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    post_id = response.json()["id"]

    # 4. Создание комментария
    comment_data = {"content": "Integration Comment"}
    response = client.post(f"/posts/{post_id}/comments", json=comment_data, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    comment_id = response.json()["id"]

    # 5. Получение поста с комментариями
    response = client.get(f"/posts/{post_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == "Integration Post"
    assert len(data["comments"]) >= 1

    # 6. Обновление поста
    update_data = {
        "title": "Updated Integration Post",
        "content": "Updated Content"
    }
    response = client.put(f"/posts/{post_id}", json=update_data, headers=headers)
    assert response.status_code == status.HTTP_200_OK

    # 7. Получение истории
    response = client.get(f"/posts/{post_id}/history")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) >= 2

    # 8. Удаление комментария
    response = client.delete(f"/comments/{comment_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK

    # 9. Удаление поста
    response = client.delete(f"/posts/{post_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK

    # 10. Проверка что пост удален
    response = client.get(f"/posts/{post_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND