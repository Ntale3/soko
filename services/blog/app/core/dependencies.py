from fastapi import Header, HTTPException
from app.core.config import settings


def get_current_user_id(x_user_id: str = Header(...)) -> str:
    return x_user_id


def internal_only(x_internal_secret: str = Header(...)):
    if x_internal_secret != settings.INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")