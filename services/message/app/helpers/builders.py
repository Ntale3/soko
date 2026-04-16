from app.models.messaging import Conversation, Message
from app.schemas.schemas import (
    ConversationOut, MessageOut, ParticipantOut
)


def make_initials(name: str) -> str:
    parts = name.strip().split()
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else name[:2].upper()


def build_conversation_out(
    conv:      Conversation,
    viewer_id: str,
) -> ConversationOut:
    is_buyer = str(conv.buyer_id) == viewer_id

    if is_buyer:
        participant = ParticipantOut(
            id=str(conv.farmer_id),
            name=conv.farmer_name,
            initials=conv.farmer_initials,
            avatar=conv.farmer_avatar,
        )
        unread = conv.buyer_unread
    else:
        participant = ParticipantOut(
            id=str(conv.buyer_id),
            name=conv.buyer_name,
            initials=conv.buyer_initials,
            avatar=conv.buyer_avatar,
        )
        unread = conv.farmer_unread

    return ConversationOut(
        id=str(conv.id),
        participant=participant,
        lastMessage=conv.last_message,
        lastMessageAt=(
            conv.last_message_at.isoformat()
            if conv.last_message_at else None
        ),
        unreadCount=unread,
        listingId=str(conv.listing_id) if conv.listing_id else None,
        listingName=conv.listing_name,
        createdAt=conv.created_at.isoformat(),
        updatedAt=conv.updated_at.isoformat(),
    )


def build_message_out(message: Message, viewer_id: str) -> MessageOut:
    return MessageOut(
        id=str(message.id),
        conversationId=str(message.conversation_id),
        senderId=str(message.sender_id),
        senderName=message.sender_name,
        senderInitials=message.sender_initials,
        body="[deleted]" if message.is_deleted else message.body,
        status=message.status.value,
        isDeleted=message.is_deleted,
        isMine=str(message.sender_id) == viewer_id,
        createdAt=message.created_at.isoformat(),
    )