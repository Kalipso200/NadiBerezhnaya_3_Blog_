from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.config import settings
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Настройка контекста для хеширования паролей
# Используем bcrypt с явным указанием backend для избежания проблем с версиями
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Количество раундов хеширования
)

# Настройка OAuth2 с указанием URL для получения токена
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/token",
    auto_error=False,  # Не выбрасывать ошибку автоматически
    scheme_name="BearerAuth"
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверка пароля

    Args:
        plain_password: пароль в открытом виде
        hashed_password: хеш пароля из БД

    Returns:
        True если пароль совпадает, иначе False
    """
    try:
        # Проверка длины пароля (bcrypt ограничение 72 байта)
        if len(plain_password.encode('utf-8')) > 72:
            logger.warning(
                f"Password too long ({len(plain_password.encode('utf-8'))} bytes), truncating to 72 bytes for verification")
            plain_password = plain_password[:72]

        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    Хеширование пароля

    Args:
        password: пароль в открытом виде

    Returns:
        Хеш пароля
    """
    try:
        # Проверка длины пароля
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            logger.warning(f"Password too long ({len(password_bytes)} bytes), truncating to 72 bytes for hashing")
            password = password[:72]

        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing password: {str(e)}"
        )


def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """
    Аутентификация пользователя

    Args:
        db: сессия базы данных
        username: имя пользователя или email
        password: пароль

    Returns:
        Объект пользователя если аутентификация успешна, иначе None
    """
    logger.info(f"Authenticating user: {username}")

    try:
        # Поиск пользователя по username или email
        user = db.query(models.User).filter(
            (models.User.username == username) | (models.User.email == username)
        ).first()

        if not user:
            logger.warning(f"User not found: {username}")
            return None

        logger.info(f"User found: {user.username}, active: {user.is_active}")

        # Проверка пароля
        if not verify_password(password, user.hashed_password):
            logger.warning(f"Invalid password for user: {username}")
            return None

        logger.info(f"Password verified for user: {username}")

        # Проверка активности пользователя
        if not user.is_active:
            logger.warning(f"Inactive user attempted login: {username}")
            return None

        logger.info(f"Authentication successful for user: {username}")
        return user

    except Exception as e:
        logger.error(f"Authentication error for user {username}: {e}")
        return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создание JWT токена доступа

    Args:
        data: данные для включения в токен
        expires_delta: время жизни токена (опционально)

    Returns:
        Строка с JWT токеном
    """
    to_encode = data.copy()

    # Установка времени истечения
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    # Создание токена
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return encoded_jwt


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> models.User:
    """
    Получение текущего пользователя по токену

    Args:
        token: JWT токен
        db: сессия базы данных

    Returns:
        Объект пользователя

    Raises:
        HTTPException: если токен невалидный или пользователь не найден
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Проверка наличия токена
    if not token:
        logger.warning("No token provided")
        raise credentials_exception

    # Обработка токена (убираем префикс Bearer если он есть)
    raw_token = token
    if token.startswith("Bearer "):
        token = token[7:]
        logger.debug("Removed Bearer prefix from token")

    logger.debug(f"Validating token: {token[:20]}...")

    try:
        # Декодирование токена
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception

        logger.debug(f"Token validated for user: {username}")
        token_data = schemas.TokenData(username=username)

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {e}")
        raise credentials_exception

    # Поиск пользователя в базе данных
    user = db.query(models.User).filter(models.User.username == token_data.username).first()

    if user is None:
        logger.warning(f"User from token not found: {token_data.username}")
        raise credentials_exception

    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    logger.debug(f"User authenticated successfully: {user.username}")
    return user


async def get_current_active_user(
        current_user: models.User = Depends(get_current_user)
) -> models.User:
    """
    Проверка активности пользователя

    Args:
        current_user: текущий пользователь из get_current_user

    Returns:
        Тот же пользователь если активен

    Raises:
        HTTPException: если пользователь неактивен
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return current_user


def check_post_permission(
        post: models.Post,
        current_user: models.User
) -> bool:
    """
    Проверка прав на пост (только автор может редактировать/удалять)

    Args:
        post: объект поста
        current_user: текущий пользователь

    Returns:
        True если пользователь является автором поста
    """
    has_permission = post.author_id == current_user.id
    if not has_permission:
        logger.warning(
            f"User {current_user.username} attempted to modify post {post.id} "
            f"owned by user {post.author_id}"
        )
    return has_permission


def create_test_user(db: Session) -> models.User:
    """
    Создание тестового пользователя (для разработки)

    Args:
        db: сессия базы данных

    Returns:
        Созданный пользователь
    """
    test_user = models.User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("TestPass123"),
        is_active=True
    )

    # Проверка существования
    existing = db.query(models.User).filter(
        (models.User.username == "testuser") | (models.User.email == "test@example.com")
    ).first()

    if existing:
        logger.info("Test user already exists")
        return existing

    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    logger.info("Test user created")
    return test_user