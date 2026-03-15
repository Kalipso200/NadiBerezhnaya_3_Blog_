"""
Скрипт для заполнения базы данных тестовыми данными
Запуск: python seed_data.py
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import random
import logging

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, engine, Base
from app import models
from app.auth import get_password_hash
from app.models import ChangeType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация тестовых данных
NUM_USERS = 5
NUM_POSTS = 20
NUM_COMMENTS = 50
DAYS_HISTORY = 30

# Список интересных заголовков постов
POST_TITLES = [
    "Мой первый пост в блоге",
    "Как я провел лето",
    "10 советов для начинающих",
    "Путешествие мечты",
    "Рецепт вкусного ужина",
    "IT-тренды 2026 года",
    "Книги, которые изменили мою жизнь",
    "Фотоотчет с выходных",
    "Мои проекты на Python",
    "FastAPI vs Django",
    "Почему я люблю программирование",
    "Как выучить иностранный язык",
    "Спорт в моей жизни",
    "Медитация для начинающих",
    "Бюджетное путешествие по Европе",
    "Как выбрать ноутбук",
    "Мои ошибки в стартапе",
    "Лучшие фильмы 2026",
    "Как найти работу мечты",
    "Саморазвитие: с чего начать"
]

# Комментарии
COMMENTS = [
    "Отличный пост! Спасибо!",
    "Очень полезная информация",
    "Согласен с автором",
    "А можно подробнее про это?",
    "Жду продолжения!",
    "Лучшее, что я читал сегодня",
    "Поделитесь опытом",
    "Интересная точка зрения",
    "Сохранил в закладки",
    "👍👍👍",
    "Наконец-то кто-то об этом написал",
    "А как насчет альтернативного мнения?",
    "Спасибо за труд!",
    "Полезно, буду пробовать",
    "Не совсем согласен, но все равно круто",
    "Понятно даже новичку",
    "Класс!",
    "Жду новых постов",
    "Подписался на вас",
    "Репостнул друзьям"
]

def create_users(db):
    """Создание тестовых пользователей"""
    logger.info("Создание пользователей...")
    users = []
    for i in range(1, NUM_USERS + 1):
        user = models.User(
            username=f"user{i}",
            email=f"user{i}@example.com",
            hashed_password=get_password_hash("TestPass123"),
            is_active=True,
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, DAYS_HISTORY))
        )
        db.add(user)
        users.append(user)
    db.commit()
    for user in users:
        db.refresh(user)
    logger.info(f"✅ Создано {len(users)} пользователей")
    return users

def create_posts(db, users):
    """Создание тестовых постов и их версий"""
    logger.info("Создание постов...")
    posts = []
    all_versions = []  # Временный список для всех версий

    for i in range(1, NUM_POSTS + 1):
        author = random.choice(users)
        created_at = datetime.now(timezone.utc) - timedelta(days=random.randint(1, DAYS_HISTORY))

        post = models.Post(
            title=random.choice(POST_TITLES) + (f" #{i}" if random.random() > 0.7 else ""),
            content=f"Это содержание поста #{i}. " + " ".join([
                "lorem ipsum dolor sit amet, consectetur adipiscing elit. " * random.randint(1, 3)
            ]),
            author_id=author.id,
            created_at=created_at,
            updated_at=created_at if random.random() > 0.8 else None
        )
        db.add(post)
        # Важно! Сбрасываем, чтобы получить ID, но не коммитим всё сразу
        db.flush()

        # Теперь у post есть ID, можно создавать версию
        version = models.PostVersion(
            post_id=post.id,  # ID уже доступен после flush
            title=post.title,
            content=post.content,
            change_type=ChangeType.CREATED,
            changed_at=post.created_at
        )
        db.add(version)
        all_versions.append(version)

        # Для некоторых постов создаем дополнительные версии (обновления)
        if random.random() > 0.7:
            version2 = models.PostVersion(
                post_id=post.id,  # ID уже доступен
                title=f"ОБНОВЛЕНО: {post.title}",
                content=post.content + "\n\n[Обновленная версия]",
                change_type=ChangeType.UPDATED,
                changed_at=post.created_at + timedelta(days=random.randint(1, 5))
            )
            db.add(version2)
            all_versions.append(version2)

        posts.append(post)

    # Теперь коммитим все изменения разом
    db.commit()
    logger.info(f"✅ Создано {len(posts)} постов")
    logger.info(f"✅ Создано {len(all_versions)} версий постов")
    return posts

def create_comments(db, users, posts):
    """Создание тестовых комментариев"""
    logger.info("Создание комментариев...")
    comments = []
    for i in range(1, NUM_COMMENTS + 1):
        author = random.choice(users)
        post = random.choice(posts)
        # Убедимся, что дата комментария не раньше даты поста
        min_comment_time = max(post.created_at, datetime.now(timezone.utc) - timedelta(days=DAYS_HISTORY))
        created_at = min_comment_time + timedelta(
            hours=random.randint(1, int((datetime.now(timezone.utc) - min_comment_time).total_seconds() / 3600))
        )

        comment = models.Comment(
            content=random.choice(COMMENTS),
            post_id=post.id,
            author_id=author.id,
            created_at=min(created_at, datetime.now(timezone.utc))
        )
        db.add(comment)
        comments.append(comment)

    db.commit()
    logger.info(f"✅ Создано {len(comments)} комментариев")
    return comments

def clear_database(db):
    """Очистка базы данных с правильным порядком (учитывая внешние ключи)"""
    logger.info("Очистка базы данных...")
    # Сначала удаляем зависимые таблицы
    db.query(models.Comment).delete()
    db.query(models.PostVersion).delete()
    db.query(models.Post).delete()
    db.query(models.User).delete()
    db.commit()
    logger.info("✅ База данных очищена")

def seed_database(clear_existing=True):
    """Главная функция заполнения БД"""
    logger.info("=" * 60)
    logger.info("НАЧАЛО ЗАПОЛНЕНИЯ ТЕСТОВЫМИ ДАННЫМИ")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        if clear_existing:
            clear_database(db)

        # Создаем данные
        users = create_users(db)
        posts = create_posts(db, users)
        comments = create_comments(db, users, posts)

        # Статистика
        logger.info("-" * 60)
        logger.info("СТАТИСТИКА СОЗДАННЫХ ДАННЫХ:")
        logger.info(f"👥 Пользователей: {len(users)}")
        logger.info(f"📝 Постов: {len(posts)}")
        logger.info(f"💬 Комментариев: {len(comments)}")

        # Дополнительная статистика
        total_versions = db.query(models.PostVersion).count()
        logger.info(f"📋 Версий постов: {total_versions}")

        active_users = db.query(models.User).filter(models.User.is_active == True).count()
        logger.info(f"✅ Активных пользователей: {active_users}")

        # Статистика по активности
        posts_with_comments = db.query(models.Post).filter(models.Post.comments.any()).count()
        logger.info(f"📊 Постов с комментариями: {posts_with_comments}")

        logger.info("=" * 60)
        logger.info("✅ ЗАПОЛНЕНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Ошибка при заполнении данных: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Заполнение БД тестовыми данными")
    parser.add_argument("--keep", action="store_true", help="Не очищать существующие данные")
    parser.add_argument("--users", type=int, default=NUM_USERS, help="Количество пользователей")
    parser.add_argument("--posts", type=int, default=NUM_POSTS, help="Количество постов")
    parser.add_argument("--comments", type=int, default=NUM_COMMENTS, help="Количество комментариев")

    args = parser.parse_args()

    # Обновляем конфигурацию из аргументов
    NUM_USERS = args.users
    NUM_POSTS = args.posts
    NUM_COMMENTS = args.comments

    seed_database(clear_existing=not args.keep)