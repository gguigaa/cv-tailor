from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import require_admin
from app.models.user import User
from app.models.cv import GeneratedCV

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UserUsage(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    total_generations: int
    last_generation: Optional[datetime]

    model_config = {"from_attributes": True}


class GenerationDetail(BaseModel):
    id: int
    lang: str
    job_description: str
    result: str
    prompt_used: Optional[str]
    cv_snapshot: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/users-usage", response_model=list[UserUsage])
def users_usage(db: Session = Depends(get_db), _=Depends(require_admin)):
    users = db.query(User).order_by(User.username).all()
    result = []
    for user in users:
        count = db.query(func.count(GeneratedCV.id)).filter(GeneratedCV.user_id == user.id).scalar()
        last = db.query(func.max(GeneratedCV.created_at)).filter(GeneratedCV.user_id == user.id).scalar()
        result.append(UserUsage(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            total_generations=count or 0,
            last_generation=last,
        ))
    return result


@router.get("/users-usage/{user_id}", response_model=list[GenerationDetail])
def user_history(
    user_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return (
        db.query(GeneratedCV)
        .filter(GeneratedCV.user_id == user_id)
        .order_by(GeneratedCV.created_at.desc())
        .all()
    )


@router.get("/generated/{cv_id}", response_model=GenerationDetail)
def generation_detail(
    cv_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return db.query(GeneratedCV).filter(GeneratedCV.id == cv_id).first()