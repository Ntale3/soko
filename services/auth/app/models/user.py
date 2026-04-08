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

class VerificationStatus(str, enum.Enum):
    unverified = "unverified"
    pending = "pending"
    verified = "verified"
    rejected = "rejected"

class User(Base):
    __tablename__ = "users"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email            = Column(String, unique=True, index=True, nullable=False)
    full_name        = Column(String, nullable=False)
    phone            = Column(String, unique=True, nullable=True)
    hashed_password  = Column(String, nullable=False)
    district         = Column(String, nullable=True)
    village          = Column(String, nullable=True)
    role             = Column(SAEnum(UserRole), default=UserRole.buyer, nullable=False)
    is_active        = Column(Boolean, default=True)
    avatar_url       = Column(String, nullable=True)

    # Farmer-specific
    farm_name        = Column(String, nullable=True)
    farmer_bio       = Column(String, nullable=True)
    specialties      = Column(String, nullable=True)  # comma-separated

    # Verification
    verified             = Column(Boolean, default=False)
    verification_status  = Column(SAEnum(VerificationStatus), default=VerificationStatus.unverified)

    # Settings
    theme                = Column(String, default="system")
    notifications_email  = Column(Boolean, default=True)
    notifications_sms    = Column(Boolean, default=False)
    notifications_push   = Column(Boolean, default=True)
    language             = Column(String, default="en")

    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)