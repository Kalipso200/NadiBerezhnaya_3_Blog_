from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from app.routers import users, posts, comments
from app.config import settings
from datetime import datetime, timezone
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO if settings.DEBUG else logging.WARNING,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

static_dir = Path("app/static")
static_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title=settings.APP_NAME,
    description="Blog API with authentication, posts, comments and versioning",
    version="1.0.0",
    debug=settings.DEBUG,
    swagger_ui_parameters={
        "persistAuthorization": True,  # Сохранять авторизацию
        "displayRequestDuration": True,
    }
)

# Настройка CORS
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"])

# Статические файлы
if static_dir.exists():
    try:
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        logger.info("Static files mounted at /static")
    except Exception as e:
        logger.warning(f"Could not mount static files: {e}")


# Настройка OpenAPI для правильной авторизации
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version="1.0.0",
        description="""
        Blog API with authentication, posts, comments and versioning.

        ## Аутентификация
        1. Получите токен через `/token` endpoint
        2. Нажмите кнопку **Authorize** и введите: `Bearer {token}`

        ### Тестовые пользователи:
        - **user1** / TestPass123
        - **user2** / TestPass123
        - **user3** / TestPass123
        - **user4** / TestPass123
        - **user5** / TestPass123
        """,
        routes=app.routes,
    )

    # Правильная настройка безопасности
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Введите токен в формате: Bearer {token}"
        }
    }

    # Применяем ко всем эндпоинтам
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            operation.setdefault("security", [{"BearerAuth": []}])

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Подключение роутеров
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(comments.router)


@app.get("/")
def root():
    return {"message": "Welcome to Blog API", "docs": "/docs", "redoc": "/redoc", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "database": "connected", "static_files": static_dir.exists(),
            "timestamp": datetime.now(timezone.utc).isoformat()}