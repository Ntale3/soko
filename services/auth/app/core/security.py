from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=10)


# Password helpers

def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    return pwd_context.verify(plain, hashed)


#  JWT helpers

def create_access_token(user_id: str, role: str, email: str) -> str:
    payload = {
        "sub":   user_id,
        "role":  role,
        "email": email,
        "type":  "access",
        "exp":   datetime.utcnow() + timedelta(
                     minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
                 ),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
        "exp":  datetime.utcnow() + timedelta(         # ✅ utcnow
                    days=settings.REFRESH_TOKEN_EXPIRE_DAYS
                ),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, token_type: str = "access") -> dict | None:
    """
    Decodes and validates a JWT token.
    token_type: "access" | "refresh" — rejects tokens of the wrong type.
    """
    try:
        data = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        if data.get("type") != token_type:
            return None
        return data
    except JWTError:
        return None