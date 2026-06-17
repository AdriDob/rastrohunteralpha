from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core_engines.ws.manager import get_ws_manager

logger = logging.getLogger("rastro.api.ws")

router = APIRouter()


@router.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")

    user_id: str | None = None
    if token:
        from core_engines.auth.auth import verify_token
        payload = verify_token(token)
        if payload:
            user_id = payload.get("sub") or payload.get("user_id")
        else:
            await websocket.close(code=4001)
            return

    manager = get_ws_manager()
    client = await manager.connect(websocket, user_id=user_id)

    try:
        while True:
            raw = await websocket.receive_text()
            await manager.handle_message(client, raw)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WS error (client=%s): %s", client.id, exc)
    finally:
        manager.disconnect(client.id)
