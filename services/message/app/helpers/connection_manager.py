import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)

# { user_id: set of WebSocket connections }
_connections: Dict[str, Set[WebSocket]] = {}


def connect(user_id: str, websocket: WebSocket):
    if user_id not in _connections:
        _connections[user_id] = set()
    _connections[user_id].add(websocket)
    logger.info(f"WS connected: {user_id} "
                f"({len(_connections[user_id])} open connections)")


def disconnect(user_id: str, websocket: WebSocket):
    if user_id in _connections:
        _connections[user_id].discard(websocket)
        if not _connections[user_id]:
            del _connections[user_id]
    logger.info(f"WS disconnected: {user_id}")


def is_online(user_id: str) -> bool:
    return bool(_connections.get(user_id))


async def send_to_user(user_id: str, payload: dict) -> bool:
    """Sends payload to all open connections for a user."""
    connections = _connections.get(user_id, set())
    if not connections:
        return False

    dead = set()
    sent = False

    for ws in set(connections):
        try:
            await ws.send_json(payload)
            sent = True
        except Exception as e:
            logger.warning(f"WS send failed for {user_id}: {e}")
            dead.add(ws)

    for ws in dead:
        _connections[user_id].discard(ws)
    if user_id in _connections and not _connections[user_id]:
        del _connections[user_id]

    return sent


async def broadcast_to_conversation(
    buyer_id:  str,
    farmer_id: str,
    payload:   dict,
    exclude:   str = None,
):
    """Sends payload to both participants, optionally skipping the sender."""
    for user_id in (buyer_id, farmer_id):
        if user_id != exclude:
            await send_to_user(user_id, payload)