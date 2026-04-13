import logging
from typing import Dict
from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Connected WebSocket clients — { user_id: WebSocket }
_connections: Dict[str, WebSocket] = {}


def register_connection(user_id: str, websocket: WebSocket):
    _connections[user_id] = websocket
    logger.info(f"WebSocket connected: {user_id}")


def remove_connection(user_id: str):
    _connections.pop(user_id, None)
    logger.info(f"WebSocket disconnected: {user_id}")


async def push_to_user(user_id: str, payload: dict) -> bool:
    """
    Sends a real-time push to a connected user.
    If they're offline the notification is already saved in DB —
    they'll see it when they open the app.
    """
    ws = _connections.get(user_id)
    if not ws:
        return False   # user offline — DB notification is the fallback

    try:
        await ws.send_json(payload)
        return True
    except Exception as e:
        logger.warning(f"WebSocket push failed for {user_id}: {e}")
        remove_connection(user_id)
        return False