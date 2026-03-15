from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
import secrets

load_dotenv()


class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "blog_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "blog_password")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "blog_db")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    DATABASE_URL: str = os.getenv("DATABASE_URL",
                                  f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # App
    APP_NAME: str = os.getenv("APP_NAME", "Blog API")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    class Config:
        env_file = ".env"
        extra = "ignore"  # Игнорировать дополнительные поля


settings = Settings()