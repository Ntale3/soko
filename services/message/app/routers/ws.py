import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.helpers.connection_manager import connect, disconnect, send_to_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/{user_id}")
async def messaging_ws(websocket: WebSocket, user_id: str):
    """
    Frontend connects here once after login.

    Client sends:
      { "event": "typing",      "conversationId": "...", "recipientId": "..." }
      { "event": "stop_typing", "conversationId": "...", "recipientId": "..." }
      { "event": "ping" }

    Client receives:
      { "event": "new_message",      "data": MessageOut }
      { "event": "message_read",     "data": { messageId, conversationId } }
      { "event": "message_deleted",  "data": { messageId, conversationId } }
      { "event": "typing",           "data": { conversationId, senderId } }
      { "event": "stop_typing",      "data": { conversationId, senderId } }
      { "event": "pong" }
    """
    await websocket.accept()
    connect(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("event")

            if event in ("typing", "stop_typing"):
                recipient_id    = data.get("recipientId")
                conversation_id = data.get("conversationId")
                if recipient_id:
                    await send_to_user(recipient_id, {
                        "event": event,
                        "data": {
                            "conversationId": conversation_id,
                            "senderId":       user_id,
                        },
                    })

            elif event == "ping":
                await websocket.send_json({"event": "pong"})

    except WebSocketDisconnect:
        disconnect(user_id, websocket)
        logger.info(f"User {user_id} disconnected from messaging WS")
    except Exception as e:
        logger.error(f"WS error for {user_id}: {e}")
        disconnect(user_id, websocket)