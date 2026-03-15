# Blog API

## Описание проекта

Blog API — это полнофункциональное REST API для блога с аутентификацией, постами, комментариями и историей изменений. Проект разработан в рамках изучения дисциплины - Спецглавы баз данных

###  Функциональность

- **CRUD для записей в блоге** — создание, чтение, обновление, удаление постов
- **Фильтрация и группировка** — поиск по заголовку, фильтр по автору и дате, сортировка
- **История изменений** — отслеживание всех изменений постов (создание, обновление, удаление)
- **Комментарии** — создание, чтение, обновление, удаление комментариев к постам
- **Аутентификация** — JWT токены, регистрация, вход
- **Авторизация** — только автор может редактировать/удалять свои посты и комментарии
- **Аналитика** — статистика постов, графики активности, топ авторов
- **Тестирование** — 34 теста, покрытие кода 59%

## Технологический стек

- **Python 3.13** — язык программирования
- **FastAPI** — веб-фреймворк
- **PostgreSQL 15** — база данных
- **SQLAlchemy 2.0** — ORM
- **Alembic** — миграции базы данных
- **Pydantic** — валидация данных
- **JWT** — аутентификация
- **passlib[bcrypt]** — хеширование паролей
- **pandas, matplotlib, seaborn** — аналитика и визуализация
- **pytest** — тестирование
- **Docker** — контейнеризация PostgreSQL

## Модель данных (ERD)

### Таблицы

#### users
| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer | Primary Key |
| username | String(50) | Уникальное имя пользователя |
| email | String(100) | Уникальный email |
| hashed_password | String(200) | Хеш пароля |
| is_active | Boolean | Активен ли пользователь |
| created_at | DateTime | Дата создания |
| updated_at | DateTime | Дата обновления |

#### posts
| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer | Primary Key |
| title | String(200) | Заголовок поста |
| content | Text | Содержание поста |
| author_id | Integer | Foreign Key → users.id |
| created_at | DateTime | Дата создания |
| updated_at | DateTime | Дата обновления |

#### post_versions
| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer | Primary Key |
| post_id | Integer | Foreign Key → posts.id |
| title | String(200) | Заголовок версии |
| content | Text | Содержание версии |
| changed_at | DateTime | Дата изменения |
| change_type | Enum | Тип изменения (created/updated/deleted) |

#### comments
| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer | Primary Key |
| content | Text | Текст комментария |
| post_id | Integer | Foreign Key → posts.id |
| author_id | Integer | Foreign Key → users.id |
| created_at | DateTime | Дата создания |
| updated_at | DateTime | Дата обновления |

### Связи

- **User** (1) ←→ (∞) **Post** — один пользователь может иметь много постов
- **User** (1) ←→ (∞) **Comment** — один пользователь может оставить много комментариев
- **Post** (1) ←→ (∞) **Comment** — один пост может иметь много комментариев
- **Post** (1) ←→ (∞) **PostVersion** — один пост может иметь много версий

##  Установка и запуск

### Предварительные требования

- Python 3.13
- Docker и Docker Compose
- PostgreSQL (опционально, если не использовать Docker)

### 1. Клонирование репозитория

```bash
git clone https://github.com/Kalipso200/NadiBerezhnaya_3_Blog_.git
cd NadiBerezhnaya_3_Blog
```
### 2. Настройка окружения
Отредактируйте .env под свои параметры:
```
# Database
POSTGRES_USER=blog_user
POSTGRES_PASSWORD=blog_password
POSTGRES_DB=blog_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql://blog_user:blog_password@localhost:5432/blog_db

# JWT
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# App
APP_NAME=Blog API
DEBUG=True
```
### 3. Запуск PostgreSQL в Docker
```bash
docker-compose -f docker-compose.db.yml up -d
```
### 4. Создание виртуального окружения и установка зависимостей
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```
### 5. Применение миграций
```
alembic upgrade head
```
### 6. Заполнение тестовыми данными (опционально)
```
python seed_data.py
```
### 7. Запуск сервера
```
uvicorn app.main:app --reload
```
Сервер будет доступен по адресу: http://localhost:8000

## Документация API
После запуска сервера документация доступна по адресам:

Swagger UI: http://localhost:8000/docs

ReDoc: http://localhost:8000/redoc

## Основные эндпоинты
### Пользователи
POST - /register - Регистрация нового пользователя - Публичный

POST - /token	- Вход в систему (получение JWT токена)	- Публичный

GET	- /users/me	- Информация о текущем пользователе	- Требуется токен

GET	- /users/{id}	- Информация о пользователе по ID	- Требуется токен
### Посты
POST	- /posts/	- Создание нового поста	- Требуется токен

GET - /posts/ -	Получение всех постов (с фильтрацией) -	Публичный

GET - /posts/stats -Статистика постов	- Публичный

GET	- /posts/{id}	- Получение поста по ID	- Публичный

PUT	- /posts/{id}	- Обновление поста	- Только автор

DELETE	- /posts/{id}	- Удаление поста	- Только автор

GET -	/posts/{id}/history	- История изменений поста	- Публичный
### Комментарии
POST	- /posts/{id}/comments - Создание комментария к посту	- Требуется токен

GET	- /posts/{id}/comments -	Получение комментариев к посту - 	Публичный

PUT	- /comments/{id}	- Обновление комментария	- Только автор

DELETE	- /comments/{id} - Удаление комментария	- Только автор

## Тестирование
```bash
# Запуск всех тестов
pytest -v
# Запуск с покрытием кода
pytest --cov=app --cov-report=term --cov-report=html
# Запуск конкретного теста
pytest tests/test_users.py::test_login_success -v
```
### Структура тестов:
* 34 теста покрывают весь функционал
* Покрытие кода: 59%
* Фикстуры обеспечивают изоляцию тестов
* Транзакции откатываются после каждого теста
