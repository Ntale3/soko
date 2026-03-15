from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8001/auth/login")


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    """
    Decodes the JWT issued by Auth service.
    Other services do NOT call Auth service over HTTP — they just verify
    the token locally using the shared SECRET_KEY.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return int(user_id), role
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def require_farmer(token: str = Depends(oauth2_scheme)):
    user_id, role = get_current_user_id(token)
    if role != "farmer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Farmers only")
    return user_id
