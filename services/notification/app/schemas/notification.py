from pydantic import BaseModel
from typing import Optional, List


class NotifyPayload(BaseModel):
    event:      str
    order_id:   Optional[str] = None
    buyer_id:   Optional[str] = None
    farmer_id:  Optional[str] = None
    message_id: Optional[str] = None
    actor_id:   Optional[str] = None
    actor_name: Optional[str] = None
    meta:       Optional[dict] = None


class NotificationOut(BaseModel):
    id:          str
    type:        str
    channel:     str
    title:       str
    body:        str
    entityType:  Optional[str]
    entityId:    Optional[str]
    isRead:      bool
    createdAt:   str


class MarkReadPayload(BaseModel):
    notification_ids: List[str]