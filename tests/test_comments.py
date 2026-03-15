"""
Тесты для комментариев
"""
import pytest
from fastapi import status

@pytest.fixture(scope="function")
def created_post(client, auth_headers):
    """Фикстура для создания поста через API"""
    response = client.post(
        "/posts/",
        json={
            "title": "Test Post for Comments",
            "content": "Test Content for Comments"
        },
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()

def test_create_comment(client, created_post, auth_headers):
    """Тест создания комментария"""
    post_id = created_post["id"]

    response = client.post(
        f"/posts/{post_id}/comments",
        json={"content": "Test comment content"},
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["content"] == "Test comment content"
    assert data["post_id"] == post_id
    assert "author" in data
    assert data["author"]["username"] == "testuser"
    return data  # Возвращаем созданный комментарий для других тестов

def test_create_comment_unauthorized(client, created_post):
    """Тест создания комментария без авторизации"""
    post_id = created_post["id"]

    response = client.post(
        f"/posts/{post_id}/comments",
        json={"content": "Test comment"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_create_comment_invalid_token(client, created_post):
    """Тест создания комментария с невалидным токеном"""
    post_id = created_post["id"]

    headers = {"Authorization": "Bearer invalid.token"}
    response = client.post(
        f"/posts/{post_id}/comments",
        json={"content": "Test comment"},
        headers=headers
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_create_comment_post_not_found(client, auth_headers):
    """Тест создания комментария к несуществующему посту"""
    response = client.post(
        "/posts/99999/comments",
        json={"content": "Test comment"},
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_get_post_comments(client, created_post, auth_headers):
    """Тест получения комментариев к посту"""
    post_id = created_post["id"]

    # Создаем комментарий
    response = client.post(
        f"/posts/{post_id}/comments",
        json={"content": "Test Comment"},
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_201_CREATED

    # Создаем дополнительный комментарий
    response2 = client.post(
        f"/posts/{post_id}/comments",
        json={"content": "Another comment"},
        headers=auth_headers
    )
    assert response2.status_code == status.HTTP_201_CREATED

    # Получаем комментарии
    response = client.get(f"/posts/{post_id}/comments")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2

def test_get_post_comments_post_not_found(client):
    """Тест получения комментариев к несуществующему посту"""
    response = client.get("/posts/99999/comments")
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_get_post_comments_pagination(client, created_post, auth_headers):
    """Тест пагинации комментариев"""
    post_id = created_post["id"]

    # Создаем несколько комментариев
    for i in range(5):
        response = client.post(
            f"/posts/{post_id}/comments",
            json={"content": f"Comment {i}"},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_201_CREATED

    response = client.get(f"/posts/{post_id}/comments?skip=0&limit=3")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 3

def test_update_comment(client, created_post, auth_headers):
    """Тест обновления комментария"""
    post_id = created_post["id"]

    # Создаем комментарий
    create_response = client.post(
        f"/posts/{post_id}/comments",
        json={"content": "Original comment"},
        headers=auth_headers
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    comment_id = create_response.json()["id"]
    print(f"Created comment with ID: {comment_id}")  # Отладка

    # Обновляем комментарий
    response = client.put(
        f"/comments/{comment_id}",
        json={"content": "Updated comment content"},
        headers=auth_headers
    )
    print(f"Update response status: {response.status_code}")  # Отладка
    if response.status_code != 200:
        print(f"Update response body: {response.text}")  # Отладка
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["content"] == "Updated comment content"
    assert data["id"] == comment_id

def test_update_comment_unauthorized(client, created_post, auth_headers):
    """Тест обновления комментария без авторизации"""
    post_id = created_post["id"]

    # Создаем комментарий
    create_response = client.post(
        f"/posts/{post_id}/comments",
        json={"content": "Original comment"},
        headers=auth_headers
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    comment_id = create_response.json()["id"]
    print(f"Created comment with ID: {comment_id}")  # Отладка

    # Пытаемся обновить без авторизации
    response = client.put(
        f"/comments/{comment_id}",
        json={"content": "Updated"}
    )
    print(f"Update unauthorized response status: {response.status_code}")  # Отладка
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_update_comment_not_found(client, auth_headers):
    """Тест обновления несуществующего комментария"""
    response = client.put(
        "/comments/99999",
        json={"content": "Updated"},
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_update_comment_wrong_user(client, created_post, auth_headers, auth_headers2):
    """Тест обновления чужого комментария"""
    post_id = created_post["id"]

    # Создаем комментарий от первого пользователя
    create_response = client.post(
        f"/posts/{post_id}/comments",
        json={"content": "Original comment"},
        headers=auth_headers
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    comment_id = create_response.json()["id"]
    print(f"Created comment with ID: {comment_id}")  # Отладка

    # Пытаемся обновить от второго пользователя
    response = client.put(
        f"/comments/{comment_id}",
        json={"content": "Updated"},
        headers=auth_headers2
    )
    print(f"Update wrong user response status: {response.status_code}")  # Отладка
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_update_comment_wrong_format(client, created_post, auth_headers, auth_headers_wrong_format):
    """Тест обновления комментария с неправильным форматом токена"""
    post_id = created_post["id"]

    # Создаем комментарий
    create_response = client.post(
        f"/posts/{post_id}/comments",
        json={"content": "Original comment"},
        headers=auth_headers
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    comment_id = create_response.json()["id"]
    print(f"Created comment with ID: {comment_id}")  # Отладка

    # Пытаемся обновить с неправильным форматом токена
    response = client.put(
        f"/comments/{comment_id}",
        json={"content": "Updated"},
        headers=auth_headers_wrong_format
    )
    print(f"Update wrong format response status: {response.status_code}")  # Отладка
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_delete_comment(client, created_post, auth_headers):
    """Тест удаления комментария"""
    post_id = created_post["id"]

    # Создаем комментарий
    create_response = client.post(
        f"/posts/{post_id}/comments",
        json={"content": "Comment to delete"},
        headers=auth_headers
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    comment_id = create_response.json()["id"]
    print(f"Created comment with ID: {comment_id}")  # Отладка

    # Удаляем комментарий
    response = client.delete(f"/comments/{comment_id}", headers=auth_headers)
    print(f"Delete response status: {response.status_code}")  # Отладка
    if response.status_code != 200:
        print(f"Delete response body: {response.text}")  # Отладка
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Comment deleted successfully"

    # Проверка что комментарий удален
    response = client.get(f"/posts/{post_id}/comments")
    data = response.json()
    assert not any(c["id"] == comment_id for c in data)

def test_delete_comment_unauthorized(client, created_post, auth_headers):
    """Тест удаления комментария без авторизации"""
    post_id = created_post["id"]

    # Создаем комментарий
    create_response = client.post(
        f"/posts/{post_id}/comments",
        json={"content": "Comment to delete"},
        headers=auth_headers
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    comment_id = create_response.json()["id"]
    print(f"Created comment with ID: {comment_id}")  # Отладка

    # Пытаемся удалить без авторизации
    response = client.delete(f"/comments/{comment_id}")
    print(f"Delete unauthorized response status: {response.status_code}")  # Отладка
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_delete_comment_not_found(client, auth_headers):
    """Тест удаления несуществующего комментария"""
    response = client.delete("/comments/99999", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_delete_comment_wrong_user(client, created_post, auth_headers, auth_headers2):
    """Тест удаления чужого комментария"""
    post_id = created_post["id"]

    # Создаем комментарий от первого пользователя
    create_response = client.post(
        f"/posts/{post_id}/comments",
        json={"content": "Original comment"},
        headers=auth_headers
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    comment_id = create_response.json()["id"]
    print(f"Created comment with ID: {comment_id}")  # Отладка

    # Пытаемся удалить от второго пользователя
    response = client.delete(f"/comments/{comment_id}", headers=auth_headers2)
    print(f"Delete wrong user response status: {response.status_code}")  # Отладка
    assert response.status_code == status.HTTP_403_FORBIDDEN