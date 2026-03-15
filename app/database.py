from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from app.config import settings
import time
import logging

logger = logging.getLogger(__name__)

def get_engine(max_retries=5, retry_interval=5):
    """Создание движка с повторными попытками подключения"""
    for attempt in range(max_retries):
        try:
            engine = create_engine(
                settings.DATABASE_URL,
                pool_pre_ping=True,
                echo=settings.DEBUG,
                pool_size=5,
                max_overflow=10,
                future=True
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.commit()
            logger.info("Successfully connected to database")
            return engine
        except SQLAlchemyError as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                logger.info(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts")
                raise

# Создаем engine
engine = get_engine()

# Создаем SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

# Создаем Base - ЭТО ВАЖНО!
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()