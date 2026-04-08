from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exception
    return user

def require_farmer(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("farmer", "both"):
        raise HTTPException(status_code=403, detail="Farmers only")
    return current_user

def require_buyer(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("buyer", "both"):
        raise HTTPException(status_code=403, detail="Buyers only")
    return current_user
