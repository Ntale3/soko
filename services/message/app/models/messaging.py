import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean,
    DateTime, Text, Integer,
    ForeignKey, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum


class MessageStatus(str, enum.Enum):
    sent      = "sent"
    delivered = "delivered"
    read      = "read"


class Conversation(Base):
    __tablename__ = "conversations"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    buyer_id         = Column(UUID(as_uuid=True), nullable=False, index=True)
    farmer_id        = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Participant snapshots
    buyer_name       = Column(String, nullable=False)
    buyer_initials   = Column(String, nullable=False)
    buyer_avatar     = Column(String, nullable=True)

    farmer_name      = Column(String, nullable=False)
    farmer_initials  = Column(String, nullable=False)
    farmer_avatar    = Column(String, nullable=True)

    # Denormalised last message
    last_message     = Column(Text,     nullable=True)
    last_message_at  = Column(DateTime, nullable=True)
    last_sender_id   = Column(UUID(as_uuid=True), nullable=True)

    # Unread counts per participant
    buyer_unread     = Column(Integer, default=0)
    farmer_unread    = Column(Integer, default=0)

    # Optional listing context
    listing_id       = Column(UUID(as_uuid=True), nullable=True)
    listing_name     = Column(String,  nullable=True)

    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id  = Column(UUID(as_uuid=True), ForeignKey("conversations.id"),
                              nullable=False, index=True)
    sender_id        = Column(UUID(as_uuid=True), nullable=False)
    sender_name      = Column(String,  nullable=False)
    sender_initials  = Column(String,  nullable=False)
    body             = Column(Text,    nullable=False)
    status           = Column(SAEnum(MessageStatus), default=MessageStatus.sent)
    is_deleted       = Column(Boolean, default=False)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")