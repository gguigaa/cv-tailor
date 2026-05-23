from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# --- Auth ---
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# --- Users (admin) ---
class UserCreate(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None
    is_admin: bool = False


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class UserOut(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- CV Profile ---
class CVProfileUpdate(BaseModel):
    cv_pt: Optional[str] = None
    cv_en: Optional[str] = None
    base_prompt: Optional[str] = None
    accent_color: Optional[str] = None


class CVProfileOut(BaseModel):
    cv_pt: Optional[str]
    cv_en: Optional[str]
    base_prompt: Optional[str]
    updated_at: Optional[datetime]
    accent_color: Optional[str]

    model_config = {"from_attributes": True}


# --- Generate ---
class GenerateRequest(BaseModel):
    job_description: str
    lang: str = "pt"
    prompt_override: Optional[str] = None


class AdjustRequest(BaseModel):
    generated_cv_id: int
    instruction: str
    conversation_history: list[dict]


class GenerateOut(BaseModel):
    id: int
    result: str
    lang: str
    job_description: str
    prompt_used: Optional[str]
    cv_snapshot: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class GeneratedCVListItem(BaseModel):
    id: int
    lang: str
    created_at: datetime
    job_snippet: str  # first 80 chars of job_description

    model_config = {"from_attributes": True}
