from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.cv import CVProfile
from app.schemas.schemas import CVProfileUpdate, CVProfileOut

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _get_or_create_profile(user: User, db: Session) -> CVProfile:
    profile = db.query(CVProfile).filter(CVProfile.user_id == user.id).first()
    if not profile:
        profile = CVProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("/", response_model=CVProfileOut)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_or_create_profile(current_user, db)


@router.put("/", response_model=CVProfileOut)
def update_profile(
    body: CVProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _get_or_create_profile(current_user, db)

    if body.cv_pt is not None:
        profile.cv_pt = body.cv_pt
    if body.cv_en is not None:
        profile.cv_en = body.cv_en
    if body.base_prompt is not None:
        profile.base_prompt = body.base_prompt

    db.commit()
    db.refresh(profile)
    return profile
