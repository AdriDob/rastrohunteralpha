"""Background scan scheduler — periodically rediscover all targets."""

import asyncio
import logging
import os

from database import db, models

logger = logging.getLogger("rastro.scheduler")


class ScanScheduler:
    """Periodically runs discovery scans on all targets."""

    def __init__(self, interval_minutes: int = 30):
        self.interval = interval_minutes * 60
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Scan scheduler started (interval=%ds)", self.interval)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Scan scheduler stopped")

    async def _loop(self):
        while self._running:
            try:
                await self._scan_all_targets()
            except Exception as exc:
                logger.warning("Scheduler cycle error: %s", exc)
            await asyncio.sleep(self.interval)

    async def _scan_all_targets(self):
        session = db.SessionLocal()
        try:
            targets = session.query(models.Target).all()
            if not targets:
                logger.debug("Scheduler: no targets to scan")
                return
            logger.info("Scheduler: scanning %d targets", len(targets))
            for target in targets:
                if not self._running:
                    break
                domain = target.domain or target.name
                try:
                    await self._scan_target(target, session)
                except Exception as exc:
                    logger.warning("Scheduler: failed to scan %s: %s", target.name, exc)
            logger.info("Scheduler: cycle complete")
        finally:
            session.close()

    async def _scan_target(self, target: models.Target, session):
        from core.orchestrator.scan_service import launch_scan

        mode = os.environ.get("RASTRO_SCAN_MODE", "FAST")
        await launch_scan(
            target_name=target.name,
            target_domain=target.domain or target.name,
            target_mode=mode,
            session=session,
        )
