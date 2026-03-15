from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from typing import Optional, List
from datetime import datetime, timedelta, timezone

# Импортируем необходимые модули
from app.database import get_db
from app import models, schemas
from app.auth import get_current_active_user, check_post_permission
from app.models import ChangeType

# ВАЖНО: создаем router
router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("/", response_model=schemas.PostOut, status_code=status.HTTP_201_CREATED)
def create_post(
        post: schemas.PostCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    """Создание нового поста"""
    db_post = models.Post(
        title=post.title,
        content=post.content,
        author_id=current_user.id
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)

    # Сохраняем первую версию
    version = models.PostVersion(
        post_id=db_post.id,
        title=db_post.title,
        content=db_post.content,
        change_type=ChangeType.CREATED
    )
    db.add(version)
    db.commit()

    return db_post


@router.get("/", response_model=List[schemas.PostListOut])
def read_posts(
        db: Session = Depends(get_db),
        skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
        limit: int = Query(100, ge=1, le=100, description="Максимальное количество записей"),
        author_id: Optional[int] = Query(None, description="Фильтр по ID автора"),
        search: Optional[str] = Query(None, description="Поиск по заголовку и содержанию"),
        date_from: Optional[datetime] = Query(None, description="Посты созданные после указанной даты"),
        date_to: Optional[datetime] = Query(None, description="Посты созданные до указанной даты"),
        sort_by: str = Query("created_at", pattern="^(created_at|title|author_id)$", description="Поле для сортировки"),
        sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Направление сортировки")
):
    """Получение списка постов с фильтрацией"""
    query = db.query(models.Post).options(joinedload(models.Post.author))

    if author_id:
        query = query.filter(models.Post.author_id == author_id)

    if search:
        query = query.filter(
            or_(
                models.Post.title.ilike(f"%{search}%"),
                models.Post.content.ilike(f"%{search}%")
            )
        )

    if date_from:
        query = query.filter(models.Post.created_at >= date_from)

    if date_to:
        query = query.filter(models.Post.created_at <= date_to)

    if sort_order == "desc":
        query = query.order_by(getattr(models.Post, sort_by).desc())
    else:
        query = query.order_by(getattr(models.Post, sort_by).asc())

    return query.offset(skip).limit(limit).all()


@router.get("/stats", response_model=dict)
def get_posts_stats(
        db: Session = Depends(get_db),
        days: int = Query(30, ge=1, le=365, description="Количество дней для статистики")
):
    """Получение статистики по постам"""
    date_from = datetime.now(timezone.utc) - timedelta(days=days)

    total_posts = db.query(models.Post).count()
    total_authors = db.query(models.Post.author_id).distinct().count()
    total_comments = db.query(models.Comment).count()

    daily_stats = db.query(
        func.date(models.Post.created_at).label('date'),
        func.count(models.Post.id).label('posts_count')
    ).filter(
        models.Post.created_at >= date_from
    ).group_by(
        func.date(models.Post.created_at)
    ).order_by('date').all()

    author_stats = db.query(
        models.User.username,
        func.count(models.Post.id).label('posts_count')
    ).join(
        models.Post, models.User.id == models.Post.author_id
    ).group_by(
        models.User.id, models.User.username
    ).order_by(
        func.count(models.Post.id).desc()
    ).limit(10).all()

    return {
        "total_posts": total_posts,
        "total_authors": total_authors,
        "total_comments": total_comments,
        "daily_stats": [
            {"date": str(stat[0]), "posts": stat[1]} for stat in daily_stats
        ],
        "top_authors": [
            {"author": stat[0], "posts": stat[1]} for stat in author_stats
        ]
    }


@router.get("/{post_id}", response_model=schemas.PostDetailOut)
def read_post(
        post_id: int,
        db: Session = Depends(get_db)
):
    """Получение детальной информации о посте"""
    db_post = db.query(models.Post).filter(
        models.Post.id == post_id
    ).options(
        joinedload(models.Post.author),
        joinedload(models.Post.comments).joinedload(models.Comment.author)
    ).first()

    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")

    return db_post


@router.put("/{post_id}", response_model=schemas.PostOut)
def update_post(
        post_id: int,
        post_update: schemas.PostUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    """Обновление поста"""
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()

    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")

    if not check_post_permission(db_post, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Сохраняем версию до обновления
    version = models.PostVersion(
        post_id=db_post.id,
        title=db_post.title,
        content=db_post.content,
        change_type=ChangeType.UPDATED
    )
    db.add(version)

    db_post.title = post_update.title
    db_post.content = post_update.content

    db.commit()
    db.refresh(db_post)

    return db_post


@router.delete("/{post_id}")
def delete_post(
        post_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    """Удаление поста"""
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()

    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")

    if not check_post_permission(db_post, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Сохраняем версию перед удалением
    version = models.PostVersion(
        post_id=db_post.id,
        title=db_post.title,
        content=db_post.content,
        change_type=ChangeType.DELETED
    )
    db.add(version)

    db.delete(db_post)
    db.commit()

    return {"message": "Post deleted successfully"}


@router.get("/{post_id}/history", response_model=List[schemas.PostVersionOut])
def get_post_history(
        post_id: int,
        db: Session = Depends(get_db),
        skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
        limit: int = Query(50, ge=1, le=100, description="Максимальное количество записей")
):
    """Получение истории изменений поста"""
    versions = db.query(models.PostVersion).filter(
        models.PostVersion.post_id == post_id
    ).order_by(
        models.PostVersion.changed_at.desc()
    ).offset(skip).limit(limit).all()

    return versions