import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base


class USSDUser(Base):
    __tablename__ = "ussd_users"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone         = Column(String, unique=True, nullable=False, index=True)
    platform_id   = Column(UUID(as_uuid=True), nullable=True)
    pin_hash      = Column(String, nullable=True)
    role          = Column(String, default="buyer")
    is_registered = Column(Boolean, default=False)
    created_at    = Column(DateTime, default=datetime.utcnow)


class USSDSession(Base):
    __tablename__ = "ussd_sessions"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id    = Column(String, unique=True, nullable=False, index=True)
    phone         = Column(String, nullable=False)
    state         = Column(String, default="main_menu")
    data          = Column(String, default="{}")
    authenticated = Column(Boolean, default=False)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)