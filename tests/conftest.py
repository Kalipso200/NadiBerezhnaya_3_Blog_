"""
Конфигурация pytest для тестов
"""
import pytest
import sys
from pathlib import Path
from typing import Dict, Any, Generator
import warnings

# Подавляем предупреждения
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", module="passlib")

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import User, Post, Comment, PostVersion, ChangeType
from app.auth import get_password_hash, create_access_token
from app.config import settings

# Создание тестовой БД (SQLite для простоты)
TEST_DATABASE_URL = "sqlite:///./test_blog.db"

# Настройки для тестовой БД
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
    future=True
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True
)

def override_get_db() -> Generator[Session, None, None]:
    """Переопределение зависимости get_db для тестов"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Подмена зависимости в приложении
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_database() -> Generator[None, None, None]:
    """Создание и очистка тестовой БД для всей сессии"""
    # Создаем таблицы
    Base.metadata.create_all(bind=engine)
    yield
    # Удаляем таблицы после всех тестов
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Фикстура для сессии БД с транзакцией"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client() -> Generator[TestClient, None, None]:
    """Фикстура для тестового клиента"""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture(scope="function")
def test_user(db_session: Session) -> User:
    """Создание тестового пользователя"""
    # Проверяем, не существует ли уже такой пользователь
    existing_user = db_session.query(User).filter(
        (User.username == "testuser") | (User.email == "test@example.com")
    ).first()

    if existing_user:
        return existing_user

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("TestPass123"),
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def test_user2(db_session: Session) -> User:
    """Создание второго тестового пользователя"""
    # Проверяем, не существует ли уже такой пользователь
    existing_user = db_session.query(User).filter(
        (User.username == "testuser2") | (User.email == "test2@example.com")
    ).first()

    if existing_user:
        return existing_user

    user = User(
        username="testuser2",
        email="test2@example.com",
        hashed_password=get_password_hash("TestPass123"),
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def test_post(db_session: Session, test_user: User) -> Post:
    """Создание тестового поста"""
    post = Post(
        title="Test Post Title",
        content="Test Post Content",
        author_id=test_user.id
    )
    db_session.add(post)
    db_session.flush()

    # Создаем версию поста
    version = PostVersion(
        post_id=post.id,
        title=post.title,
        content=post.content,
        change_type=ChangeType.CREATED,
        changed_at=post.created_at
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(post)

    return post

@pytest.fixture(scope="function")
def test_comment(db_session: Session, test_post: Post, test_user2: User) -> Comment:
    """Создание тестового комментария"""
    comment = Comment(
        content="Test Comment",
        post_id=test_post.id,
        author_id=test_user2.id
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)
    return comment

@pytest.fixture(scope="function")
def test_user_token(test_user: User) -> str:
    """Создание токена для тестового пользователя"""
    token = create_access_token(data={"sub": test_user.username})
    return token

@pytest.fixture(scope="function")
def test_user2_token(test_user2: User) -> str:
    """Создание токена для второго тестового пользователя"""
    token = create_access_token(data={"sub": test_user2.username})
    return token

@pytest.fixture(scope="function")
def auth_headers(test_user_token: str) -> Dict[str, str]:
    """Заголовки авторизации с правильным Bearer форматом"""
    return {"Authorization": f"Bearer {test_user_token}"}

@pytest.fixture(scope="function")
def auth_headers2(test_user2_token: str) -> Dict[str, str]:
    """Заголовки авторизации для второго пользователя"""
    return {"Authorization": f"Bearer {test_user2_token}"}

@pytest.fixture(scope="function")
def auth_headers_wrong_format(test_user_token: str) -> Dict[str, str]:
    """Заголовки авторизации с неправильным форматом (без Bearer)"""
    return {"Authorization": test_user_token}

@pytest.fixture(scope="function")
def test_posts_bulk(db_session: Session, test_user: User) -> list[Post]:
    """Создание нескольких тестовых постов"""
    posts = []
    for i in range(5):
        post = Post(
            title=f"Test Post {i}",
            content=f"Test Content {i}",
            author_id=test_user.id
        )
        db_session.add(post)
        db_session.flush()

        version = PostVersion(
            post_id=post.id,
            title=post.title,
            content=post.content,
            change_type=ChangeType.CREATED,
            changed_at=post.created_at
        )
        db_session.add(version)
        posts.append(post)

    db_session.commit()
    for post in posts:
        db_session.refresh(post)
    return posts

@pytest.fixture(scope="function")
def test_comments_bulk(db_session: Session, test_post: Post, test_user2: User) -> list[Comment]:
    """Создание нескольких тестовых комментариев"""
    comments = []
    for i in range(3):
        comment = Comment(
            content=f"Test Comment {i}",
            post_id=test_post.id,
            author_id=test_user2.id
        )
        db_session.add(comment)
        comments.append(comment)

    db_session.commit()
    for comment in comments:
        db_session.refresh(comment)
    return comments

@pytest.fixture(scope="function")
def inactive_user(db_session: Session) -> User:
    """Создание неактивного пользователя"""
    user = User(
        username="inactive",
        email="inactive@example.com",
        hashed_password=get_password_hash("TestPass123"),
        is_active=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def admin_user(db_session: Session) -> User:
    """Создание администратора (если есть поле is_admin)"""
    # В этой модели нет is_admin, но оставим для совместимости
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("AdminPass123"),
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def clean_database(db_session: Session) -> None:
    """Очистка всех таблиц (для тестов, где нужна полная изоляция)"""
    db_session.query(Comment).delete()
    db_session.query(PostVersion).delete()
    db_session.query(Post).delete()
    db_session.query(User).delete()
    db_session.commit()

@pytest.fixture(scope="function")
def sample_post_data() -> Dict[str, Any]:
    """Тестовые данные для создания поста"""
    return {
        "title": "Sample Post",
        "content": "Sample Content"
    }

@pytest.fixture(scope="function")
def sample_comment_data() -> Dict[str, Any]:
    """Тестовые данные для создания комментария"""
    return {
        "content": "Sample Comment"
    }

@pytest.fixture(scope="function")
def sample_user_data() -> Dict[str, Any]:
    """Тестовые данные для регистрации пользователя"""
    return {
        "username": "sampleuser",
        "email": "sample@example.com",
        "password": "SamplePass123"
    }

@pytest.fixture(scope="function")
def sample_login_data() -> Dict[str, Any]:
    """Тестовые данные для входа"""
    return {
        "username": "testuser",
        "password": "TestPass123"
    }

@pytest.fixture(scope="function")
def invalid_token() -> str:
    """Невалидный токен"""
    return "invalid.token.here"

@pytest.fixture(scope="function")
def expired_token() -> str:
    """Истекший токен (создается отдельно в тестах)"""
    return "expired.token.here"

@pytest.fixture(scope="function")
def check_db_connection(db_session: Session) -> bool:
    """Проверка подключения к БД"""
    try:
        db_session.execute(text("SELECT 1"))
        return True
    except:
        return False

# Хуки для pytest
def pytest_configure(config):
    """Конфигурация pytest при запуске"""
    config.addinivalue_line(
        "markers",
        "slow: тесты, которые выполняются долго"
    )
    config.addinivalue_line(
        "markers",
        "integration: интеграционные тесты"
    )
    config.addinivalue_line(
        "markers",
        "unit: модульные тесты"
    )
    config.addinivalue_line(
        "markers",
        "auth: тесты авторизации"
    )
    config.addinivalue_line(
        "markers",
        "posts: тесты постов"
    )
    config.addinivalue_line(
        "markers",
        "comments: тесты комментариев"
    )
    config.addinivalue_line(
        "markers",
        "users: тесты пользователей"
    )
    config.addinivalue_line(
        "markers",
        "db: тесты с подключением к БД"
    )
    config.addinivalue_line(
        "markers",
        "api: тесты API эндпоинтов"
    )

def pytest_collection_modifyitems(items):
    """Модификация собранных тестов перед запуском"""
    for item in items:
        # Добавляем маркер db для тестов, использующих db_session
        if "db_session" in item.fixturenames:
            item.add_marker("db")

        # Добавляем маркер api для тестов, использующих client
        if "client" in item.fixturenames:
            item.add_marker("api")

        # Добавляем маркер auth для тестов авторизации
        if "auth" in item.name or "token" in item.name:
            item.add_marker("auth")

        # Добавляем маркер users для тестов пользователей
        if "user" in item.name and "test_user" in item.fixturenames:
            item.add_marker("users")

        # Добавляем маркер posts для тестов постов
        if "post" in item.name and "test_post" in item.fixturenames:
            item.add_marker("posts")

        # Добавляем маркер comments для тестов комментариев
        if "comment" in item.name and "test_comment" in item.fixturenames:
            item.add_marker("comments")