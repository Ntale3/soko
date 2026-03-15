from pydantic import BaseModel, EmailStr
from datetime import datetime
from app.models.user import UserRole


# ── Request schemas ──────────────────────────────────────────────────
class UserRegister(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: UserRole = UserRole.buyer


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ── Response schemas ─────────────────────────────────────────────────
class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int | None = None
    role: UserRole | None = None
