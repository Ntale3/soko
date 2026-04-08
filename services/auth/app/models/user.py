import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
import enum

class UserRole(str, enum.Enum):
    farmer = "farmer"
    buyer = "buyer"
    both = "both"
    admin = "admin"

class AuthCredential(Base):
    __tablename__ = "auth_credentials"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email            = Column(String, unique=True, index=True, nullable=False)
    hashed_password  = Column(String, nullable=True)   # nullable for OAuth users
    role             = Column(SAEnum(UserRole), default=UserRole.buyer, nullable=False)
    avatar_url       = Column(String, nullable=True)
    is_active        = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)