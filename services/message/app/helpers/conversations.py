import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
import httpx

from app.core.config import settings
from app.core.dependencies import get_current_user_id
from app.db.database import get_db
from app.helpers.builders import (
    build_conversation_out,
    build_message_out,
    make_initials,
)
from app.models.messaging import Conversation, Message, MessageStatus
from app.schemas.schemas import (
    ConversationOut,
    ConversationDetailOut,
    StartConversationPayload,
    StartConversationOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Conversations"])


async def fetch_user(user_id: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{settings.USER_SERVICE_URL}/users/{user_id}",
                headers={"x-internal-secret": settings.INTERNAL_SECRET},
                timeout=5.0,
            )
            if res.status_code == 200:
                return res.json()
    except Exception as e:
        logger.warning(f"Could not fetch user {user_id}: {e}")
    return {}


async def fetch_listing(listing_id: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{settings.PRODUCE_SERVICE_URL}/listings/slug/{listing_id}",
                timeout=5.0,
            )
            if res.status_code == 200:
                return res.json()
    except Exception as e:
        logger.warning(f"Could not fetch listing {listing_id}: {e}")
    return {}


# ── Get all conversations for current user
@router.get("", response_model=list[ConversationOut])
def get_conversations(
    page:    int = Query(default=1,  ge=1),
    limit:   int = Query(default=30, le=100),
    user_id: str = Depends(get_current_user_id),
    db:      Session = Depends(get_db),
):
    convs = db.query(Conversation).filter(
        or_(
            Conversation.buyer_id  == uuid.UUID(user_id),
            Conversation.farmer_id == uuid.UUID(user_id),
        )
    ).order_by(Conversation.last_message_at.desc().nullslast()) \
     .offset((page - 1) * limit).limit(limit).all()

    return [build_conversation_out(c, viewer_id=user_id) for c in convs]


# ── Start a new conversation or reuse existing
@router.post("", response_model=StartConversationOut, status_code=201)
async def start_conversation(
    payload:     StartConversationPayload,
    user_id:     str     = Depends(get_current_user_id),
    db:          Session = Depends(get_db),
):
    # Prevent a farmer messaging themselves
    if user_id == payload.farmer_id:
        raise HTTPException(status_code=400, detail="Cannot message yourself")

    # Check if conversation already exists
    existing = db.query(Conversation).filter(
        and_(
            Conversation.buyer_id  == uuid.UUID(user_id),
            Conversation.farmer_id == uuid.UUID(payload.farmer_id),
        )
    ).first()

    if existing:
        # Add message to existing conversation
        msg = Message(
            conversation_id=existing.id,
            sender_id=uuid.UUID(user_id),
            sender_name=existing.buyer_name,
            sender_initials=existing.buyer_initials,
            body=payload.first_message,
        )
        db.add(msg)
        existing.last_message    = payload.first_message
        existing.last_message_at = datetime.utcnow()
        existing.last_sender_id  = uuid.UUID(user_id)
        existing.farmer_unread  += 1
        db.commit()
        db.refresh(existing)
        db.refresh(msg)

        return StartConversationOut(
            conversation=build_conversation_out(existing, viewer_id=user_id),
            message=build_message_out(msg, viewer_id=user_id),
            isNew=False,
        )

    # ── Fetch participant snapshots
    buyer  = await fetch_user(user_id)
    farmer = await fetch_user(payload.farmer_id)

    if not buyer or not farmer:
        raise HTTPException(status_code=404, detail="One or both users not found")

    listing_name = None
    listing_uuid = None
    if payload.listing_id:
        listing      = await fetch_listing(payload.listing_id)
        listing_name = listing.get("name")
        try:
            listing_uuid = uuid.UUID(payload.listing_id)
        except ValueError:
            listing_uuid = None

    conv = Conversation(
        buyer_id=uuid.UUID(user_id),
        farmer_id=uuid.UUID(payload.farmer_id),
        buyer_name=buyer.get("name", ""),
        buyer_initials=buyer.get("initials") or make_initials(buyer.get("name", "B")),
        buyer_avatar=buyer.get("avatarUrl"),
        farmer_name=farmer.get("name", ""),
        farmer_initials=farmer.get("initials") or make_initials(farmer.get("name", "F")),
        farmer_avatar=farmer.get("avatarUrl"),
        listing_id=listing_uuid,
        listing_name=listing_name,
        last_message=payload.first_message,
        last_message_at=datetime.utcnow(),
        last_sender_id=uuid.UUID(user_id),
        farmer_unread=1,
        buyer_unread=0,
    )
    db.add(conv)
    db.flush()

    msg = Message(
        conversation_id=conv.id,
        sender_id=uuid.UUID(user_id),
        sender_name=conv.buyer_name,
        sender_initials=conv.buyer_initials,
        body=payload.first_message,
    )
    db.add(msg)
    db.commit()
    db.refresh(conv)
    db.refresh(msg)

    return StartConversationOut(
        conversation=build_conversation_out(conv, viewer_id=user_id),
        message=build_message_out(msg, viewer_id=user_id),
        isNew=True,
    )


# ── Get single conversation with message history
@router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(
    conversation_id: str,
    page:    int = Query(default=1,  ge=1),
    limit:   int = Query(default=50, le=100),
    user_id: str = Depends(get_current_user_id),
    db:      Session = Depends(get_db),
):
    conv = db.query(Conversation).filter(
        Conversation.id == uuid.UUID(conversation_id),
        or_(
            Conversation.buyer_id  == uuid.UUID(user_id),
            Conversation.farmer_id == uuid.UUID(user_id),
        )
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.query(Message).filter(
        Message.conversation_id == uuid.UUID(conversation_id)
    ).order_by(Message.created_at.asc()) \
     .offset((page - 1) * limit).limit(limit).all()

    # Mark all unread messages from the other person as delivered
    db.query(Message).filter(
        Message.conversation_id == uuid.UUID(conversation_id),
        Message.sender_id       != uuid.UUID(user_id),
        Message.status          == MessageStatus.sent,
    ).update({"status": MessageStatus.delivered}, synchronize_session=False)

    # Reset unread count for viewer
    is_buyer = str(conv.buyer_id) == user_id
    if is_buyer:
        conv.buyer_unread = 0
    else:
        conv.farmer_unread = 0

    db.commit()

    return ConversationDetailOut(
        conversation=build_conversation_out(conv, viewer_id=user_id),
        messages=[build_message_out(m, viewer_id=user_id) for m in messages],
    )