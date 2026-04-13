import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import httpx

from app.core.config import settings
from app.core.dependencies import internal_only
from app.db.database import get_db
from app.helpers.sms import send_sms
from app.helpers.push import push_to_user
from app.helpers.templates import get_template
from app.models.notification import Notification, NotificationType, NotificationChannel
from services.notification.app.schemas.notification import NotifyPayload

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Internal"], dependencies=[Depends(internal_only)])

# Events that also trigger an SMS
SMS_EVENTS = {
    "order_placed",
    "payment_confirmed",
    "payment_failed",
    "order_dispatched",
}


async def fetch_user(user_id: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{settings.USER_SERVICE_URL}/users/{user_id}",
                headers={"x-internal-secret": settings.INTERNAL_SECRET},
                timeout=5.0
            )
            if res.status_code == 200:
                return res.json()
    except Exception as e:
        logger.warning(f"Could not fetch user {user_id}: {e}")
    return {}


async def deliver_notification(
    db:          Session,
    user_id:     str,
    event:       str,
    role:        str,        # "buyer" | "farmer" | "recipient"
    entity_id:   str | None,
    meta:        dict,
    send_sms_:   bool = False,
    phone:       str  = None,
):
    """
    Creates a DB notification record and attempts real-time delivery.
    """
    templates = get_template(event, meta)
    template  = templates.get(role)
    if not template:
        return

    # ── Save in-app notification
    notif = Notification(
        user_id=uuid.UUID(user_id),
        type=NotificationType(event),
        channel=NotificationChannel.in_app,
        title=template.title,
        body=template.body,
        entity_type=template.entity_type,
        entity_id=entity_id,
        is_read=False,
        sent=True,
        sent_at=datetime.utcnow(),
    )
    db.add(notif)
    db.commit()

    # ── Real-time push (WebSocket)
    await push_to_user(user_id, {
        "id":         str(notif.id),
        "type":       event,
        "title":      template.title,
        "body":       template.body,
        "entityType": template.entity_type,
        "entityId":   entity_id,
        "createdAt":  notif.created_at.isoformat(),
    })

    # ── SMS for important events
    if send_sms_ and phone and event in SMS_EVENTS:
        db.add(Notification(
            user_id=uuid.UUID(user_id),
            type=NotificationType(event),
            channel=NotificationChannel.sms,
            title=template.title,
            body=template.body,
            entity_type=template.entity_type,
            entity_id=entity_id,
            sent=send_sms(phone, template.body),
            sent_at=datetime.utcnow(),
        ))
        db.commit()


@router.post("/notify")
async def notify(payload: NotifyPayload, db: Session = Depends(get_db)):
    """
    Central notification dispatcher.
    Any service posts here with an event and relevant IDs.
    """
    event = payload.event
    meta  = payload.meta or {}

    # ── Order events — notify buyer and/or farmer
    if payload.order_id:
        meta["order_ref"] = f"#{payload.order_id[:8].upper()}"

    if payload.buyer_id:
        buyer = await fetch_user(payload.buyer_id)
        meta.update({
            "product": meta.get("product", "your order"),
        })
        await deliver_notification(
            db=db,
            user_id=payload.buyer_id,
            event=event,
            role="buyer",
            entity_id=payload.order_id,
            meta=meta,
            send_sms_=True,
            phone=buyer.get("phone"),
        )

    if payload.farmer_id:
        farmer = await fetch_user(payload.farmer_id)
        await deliver_notification(
            db=db,
            user_id=payload.farmer_id,
            event=event,
            role="farmer",
            entity_id=payload.order_id,
            meta=meta,
            send_sms_=False,    # farmers get push only — not SMS for every order
            phone=farmer.get("phone"),
        )

    # ── Message notification
    if event == "new_message" and payload.actor_id:
        meta["actor_name"] = payload.actor_name or "Someone"
        await deliver_notification(
            db=db,
            user_id=payload.actor_id,
            event=event,
            role="recipient",
            entity_id=payload.message_id,
            meta=meta,
        )

    # ── Review notification — tell farmer
    if event == "new_review" and payload.farmer_id:
        meta["actor_name"] = payload.actor_name or "A buyer"
        await deliver_notification(
            db=db,
            user_id=payload.farmer_id,
            event=event,
            role="farmer",
            entity_id=payload.order_id,
            meta=meta,
        )

    # ── Follow notification — tell farmer
    if event == "new_follower" and payload.farmer_id:
        meta["actor_name"] = payload.actor_name or "Someone"
        await deliver_notification(
            db=db,
            user_id=payload.farmer_id,
            event=event,
            role="farmer",
            entity_id=payload.actor_id,
            meta=meta,
        )

    return {"dispatched": True}