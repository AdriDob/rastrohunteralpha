from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("rastro.ws.bridge")


def start_event_bridge() -> None:
    from core_engines.events.event_bus import get_event_bus
    from core_engines.ws.manager import get_ws_manager

    bus = get_event_bus()
    manager = get_ws_manager()

    async def _on_event(event_type: str, **payload: Any) -> None:
        if manager.active_count == 0:
            return
        await manager.broadcast(event_type, payload)

    bus.subscribe_async("*", _on_event)
    logger.info("Event bus → WebSocket bridge started")
