"""
Тесты для постов
"""
import pytest
from fastapi import status

def test_get_post_history(client, test_post, auth_headers):
    """Тест получения истории поста"""
    # Создаем несколько обновлений
    for i in range(3):
        response = client.put(
            f"/posts/{test_post.id}",
            json={
                "title": f"Updated Title {i}",
                "content": f"Updated Content {i}"
            },
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK

    response = client.get(f"/posts/{test_post.id}/history")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 4  # 1 создание + 3 обновления
    # Проверяем что среди версий есть обновления
    change_types = [item["change_type"] for item in data]
    assert any(ct in ["updated", "UPDATED"] for ct in change_types), "Нет обновлений в истории"