import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)

_connections: Dict[str, Set[WebSocket]] = {}


def register_connection(user_id: str, websocket: WebSocket):
    if user_id not in _connections:
        _connections[user_id] = set()
    _connections[user_id].add(websocket)


def remove_connection(user_id: str, websocket: WebSocket):
    if user_id in _connections:
        _connections[user_id].discard(websocket)
        if not _connections[user_id]:
            del _connections[user_id]


async def push_to_user(user_id: str, payload: dict) -> bool:
    connections = _connections.get(user_id, set())
    if not connections:
        return False

    dead = set()
    sent = False
    for ws in connections:
        try:
            await ws.send_json(payload)
            sent = True
        except Exception as e:
            logger.warning(f"WS push failed for {user_id}: {e}")
            dead.add(ws)

    for ws in dead:
        _connections[user_id].discard(ws)

    return sent