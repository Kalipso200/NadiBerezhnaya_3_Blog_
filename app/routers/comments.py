"""
Роутер для комментариев
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List
from app import models, schemas, auth
from app.database import get_db

router = APIRouter(tags=["comments"])

@router.post("/posts/{post_id}/comments", response_model=schemas.CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(
        post_id: int,
        comment: schemas.CommentCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    """Создание комментария к посту"""
    # Проверяем существование поста
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Создаем комментарий
    db_comment = models.Comment(
        content=comment.content,
        post_id=post_id,
        author_id=current_user.id
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)

    # Загружаем информацию об авторе
    db_comment = db.query(models.Comment).options(
        joinedload(models.Comment.author)
    ).filter(models.Comment.id == db_comment.id).first()

    return db_comment


@router.get("/posts/{post_id}/comments", response_model=List[schemas.CommentOut])
def get_post_comments(
        post_id: int,
        db: Session = Depends(get_db),
        skip: int = Query(0, ge=0, description="Количество пропускаемых комментариев"),
        limit: int = Query(50, ge=1, le=100, description="Максимальное количество комментариев")
):
    """Получение всех комментариев к посту"""
    # Проверяем существование поста
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Получаем комментарии
    comments = db.query(models.Comment).options(
        joinedload(models.Comment.author)
    ).filter(
        models.Comment.post_id == post_id
    ).order_by(
        models.Comment.created_at.desc()
    ).offset(skip).limit(limit).all()

    return comments


@router.put("/comments/{comment_id}", response_model=schemas.CommentOut)
def update_comment(
        comment_id: int,
        comment_update: schemas.CommentUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    """Обновление комментария"""
    # Получаем комментарий с информацией об авторе
    db_comment = db.query(models.Comment).options(
        joinedload(models.Comment.author)
    ).filter(models.Comment.id == comment_id).first()

    if not db_comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Проверка прав (только автор может редактировать)
    if db_comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Обновляем комментарий
    db_comment.content = comment_update.content
    db.commit()
    db.refresh(db_comment)

    return db_comment


@router.delete("/comments/{comment_id}")
def delete_comment(
        comment_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    """Удаление комментария"""
    # Получаем комментарий
    db_comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()

    if not db_comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Проверка прав (только автор может удалять)
    if db_comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Удаляем комментарий
    db.delete(db_comment)
    db.commit()

    return {"message": "Comment deleted successfully"}