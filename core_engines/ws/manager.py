from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger("rastro.ws")

CLIENT_EVENT_SUBSCRIBE = "subscribe"
CLIENT_EVENT_UNSUBSCRIBE = "unsubscribe"
CLIENT_EVENT_PING = "ping"

SERVER_EVENT_MESSAGE = "message"
SERVER_EVENT_PONG = "pong"
SERVER_EVENT_ERROR = "error"


class WSClient:
    def __init__(self, websocket: WebSocket, user_id: Optional[str] = None) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.websocket = websocket
        self.user_id = user_id
        self.subscriptions: Set[str] = set()
        self.connected_at = time.time()
        self._last_pong = time.time()

    def subscribed_to(self, event_type: str) -> bool:
        if not self.subscriptions:
            return True
        for pattern in self.subscriptions:
            if pattern.endswith("*") and event_type.startswith(pattern.rstrip("*")):
                return True
            if pattern == event_type:
                return True
        return False

    @property
    def age_seconds(self) -> float:
        return time.time() - self.connected_at


class WSManager:
    def __init__(self) -> None:
        self._clients: Dict[str, WSClient] = {}

    @property
    def active_count(self) -> int:
        return len(self._clients)

    @property
    def clients(self) -> list[WSClient]:
        return list(self._clients.values())

    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None) -> WSClient:
        await websocket.accept()
        client = WSClient(websocket, user_id=user_id)
        self._clients[client.id] = client
        logger.info("WS client connected: %s (user=%s, total=%d)", client.id, user_id, self.active_count)
        return client

    def disconnect(self, client_id: str) -> None:
        self._clients.pop(client_id, None)
        logger.info("WS client disconnected: %s (total=%d)", client_id, self.active_count)

    async def broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
        msg = json.dumps({"type": event_type, "payload": payload, "ts": time.time()})
        dead: list[str] = []
        for cid, client in self._clients.items():
            if not client.subscribed_to(event_type):
                continue
            try:
                await client.websocket.send_text(msg)
            except Exception:
                dead.append(cid)
        for cid in dead:
            self.disconnect(cid)

    async def send_to(self, client_id: str, event_type: str, payload: Dict[str, Any]) -> bool:
        client = self._clients.get(client_id)
        if not client:
            return False
        try:
            await client.websocket.send_text(json.dumps({"type": event_type, "payload": payload, "ts": time.time()}))
            return True
        except Exception:
            self.disconnect(client_id)
            return False

    async def handle_message(self, client: WSClient, raw: str) -> None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            await self.send_to(client.id, SERVER_EVENT_ERROR, {"error": "invalid JSON"})
            return

        msg_type = data.get("type")
        if msg_type == CLIENT_EVENT_SUBSCRIBE:
            pattern = data.get("pattern", "*")
            client.subscriptions.add(pattern)
            logger.debug("WS %s subscribed to %s", client.id, pattern)
        elif msg_type == CLIENT_EVENT_UNSUBSCRIBE:
            pattern = data.get("pattern")
            client.subscriptions.discard(pattern)
        elif msg_type == CLIENT_EVENT_PING:
            client._last_pong = time.time()
            await self.send_to(client.id, SERVER_EVENT_PONG, {})


_MANAGER: Optional[WSManager] = None


def get_ws_manager() -> WSManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = WSManager()
        logger.info("WS manager initialized")
    return _MANAGER
