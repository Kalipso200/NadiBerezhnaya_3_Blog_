from pydantic import BaseModel, EmailStr, Field, ConfigDict, validator
from datetime import datetime
from typing import Optional, List, ForwardRef
from app.models import ChangeType
import re


# ==================== User Schemas ====================

class UserBase(BaseModel):
    """Базовая схема пользователя"""
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username, must be unique",
        example="john_doe"
    )
    email: EmailStr = Field(
        ...,
        description="Email address, must be unique",
        example="john@example.com"
    )


class UserCreate(UserBase):
    """Схема для создания пользователя (регистрации)"""
    password: str = Field(
        ...,
        min_length=8,
        description="Password. Must be at least 8 characters, contain uppercase, lowercase and digit",
        example="SecurePass123"
    )

    @validator('password')
    def validate_password(cls, v):
        """
        Валидация пароля:
        - Минимум 8 символов
        - Максимум 72 байта (ограничение bcrypt)
        - Хотя бы одна заглавная буква
        - Хотя бы одна строчная буква
        - Хотя бы одна цифра
        """
        # Проверка длины в байтах (для bcrypt)
        password_bytes = v.encode('utf-8')
        if len(password_bytes) > 72:
            byte_count = len(password_bytes)
            char_count = len(v)
            raise ValueError(
                f'Password too long for bcrypt. '
                f'Maximum 72 bytes (current: {byte_count} bytes, {char_count} characters). '
                f'This limit is a security feature of the bcrypt algorithm.'
            )

        # Проверка наличия заглавных букв
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')

        # Проверка наличия строчных букв
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')

        # Проверка наличия цифр
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')

        # Опционально: проверка наличия специальных символов
        # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
        #     raise ValueError('Password must contain at least one special character')

        return v


class UserLogin(BaseModel):
    """Схема для входа пользователя"""
    username: str = Field(
        ...,
        description="Username or email",
        example="john_doe"
    )
    password: str = Field(
        ...,
        description="Password",
        example="SecurePass123"
    )


class UserOut(UserBase):
    """Схема для вывода информации о пользователе"""
    id: int = Field(..., description="User ID")
    is_active: bool = Field(..., description="Is user active")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = ConfigDict(from_attributes=True)


# ==================== Token Schemas ====================

class Token(BaseModel):
    """Схема для JWT токена"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Token type (bearer)", example="bearer")


class TokenData(BaseModel):
    """Схема для данных в токене"""
    username: Optional[str] = Field(None, description="Username from token")


# ==================== Post Schemas ====================

class PostBase(BaseModel):
    """Базовая схема поста"""
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Post title",
        example="My First Blog Post"
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Post content",
        example="This is the content of my first blog post..."
    )


class PostCreate(PostBase):
    """Схема для создания поста"""
    pass


class PostUpdate(PostBase):
    """Схема для обновления поста"""
    pass


class PostOut(PostBase):
    """Схема для вывода информации о посте"""
    id: int = Field(..., description="Post ID")
    author_id: int = Field(..., description="Author ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class PostListOut(PostOut):
    """Схема для списка постов с информацией об авторе"""
    author: UserOut = Field(..., description="Author information")

    model_config = ConfigDict(from_attributes=True)


# Используем ForwardRef для избежания циклических ссылок
CommentOut = ForwardRef('CommentOut')


class PostDetailOut(PostListOut):
    """Схема для детальной информации о посте с комментариями"""
    comments: List[CommentOut] = Field(default_factory=list, description="Post comments")

    model_config = ConfigDict(from_attributes=True)


# ==================== PostVersion Schemas ====================

class PostVersionBase(BaseModel):
    """Базовая схема версии поста"""
    title: str = Field(..., description="Post title at that version")
    content: str = Field(..., description="Post content at that version")
    change_type: ChangeType = Field(..., description="Type of change")


class PostVersionOut(PostVersionBase):
    """Схема для вывода информации о версии поста"""
    id: int = Field(..., description="Version ID")
    post_id: int = Field(..., description="Original post ID")
    changed_at: datetime = Field(..., description="When the change occurred")

    model_config = ConfigDict(from_attributes=True)


# ==================== Comment Schemas ====================

class CommentBase(BaseModel):
    """Базовая схема комментария"""
    content: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Comment content",
        example="Great post! Thanks for sharing."
    )


class CommentCreate(CommentBase):
    """Схема для создания комментария"""
    pass


class CommentUpdate(CommentBase):
    """Схема для обновления комментария"""
    pass


class CommentOut(CommentBase):
    """Схема для вывода информации о комментарии"""
    id: int = Field(..., description="Comment ID")
    post_id: int = Field(..., description="Post ID")
    author_id: int = Field(..., description="Author ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    author: UserOut = Field(..., description="Author information")

    model_config = ConfigDict(from_attributes=True)


# ==================== Update ForwardRefs ====================

# Обновляем ссылки после определения всех классов
PostDetailOut.model_rebuild()
CommentOut.model_rebuild()


# ==================== Additional Schemas ====================

class PasswordChange(BaseModel):
    """Схема для смены пароля"""
    old_password: str = Field(
        ...,
        description="Current password",
        example="OldPass123"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        description="New password",
        example="NewPass456"
    )

    @validator('new_password')
    def validate_new_password(cls, v):
        """Валидация нового пароля"""
        # Можно использовать ту же логику что и для регистрации
        password_bytes = v.encode('utf-8')
        if len(password_bytes) > 72:
            raise ValueError('New password too long for bcrypt (max 72 bytes)')

        if not re.search(r'[A-Z]', v):
            raise ValueError('New password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('New password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('New password must contain at least one digit')

        return v


class UserUpdate(BaseModel):
    """Схема для обновления информации о пользователе"""
    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        description="New username"
    )
    email: Optional[EmailStr] = Field(
        None,
        description="New email"
    )


class Message(BaseModel):
    """Простая схема для сообщений"""
    message: str = Field(..., description="Response message")
    detail: Optional[str] = Field(None, description="Additional details")


class HealthCheck(BaseModel):
    """Схема для проверки здоровья"""
    status: str = Field(..., description="Service status")
    database: str = Field(..., description="Database status")
    timestamp: datetime = Field(..., description="Current timestamp")


class PostStats(BaseModel):
    """Схема для статистики постов"""
    total_posts: int = Field(..., description="Total number of posts")
    total_authors: int = Field(..., description="Total number of authors")
    total_comments: int = Field(..., description="Total number of comments")
    daily_stats: List[dict] = Field(..., description="Daily statistics")
    top_authors: List[dict] = Field(..., description="Top authors by posts")


# ==================== Example responses for documentation ====================

# Примеры ответов для документации
user_example = {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "is_active": True,
    "created_at": "2024-01-01T00:00:00Z"
}

post_example = {
    "id": 1,
    "title": "My First Post",
    "content": "This is my first post content",
    "author_id": 1,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": None
}

comment_example = {
    "id": 1,
    "content": "Great post!",
    "post_id": 1,
    "author_id": 2,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": None,
    "author": user_example
}