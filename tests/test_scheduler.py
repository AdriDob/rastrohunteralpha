"""Tests for the background scan scheduler."""

from __future__ import annotations

import asyncio


class TestScheduler:
    """Verify scheduler instantiation and lifecycle."""

    def test_scheduler_create(self):
        from api.scheduler import ScanScheduler
        sched = ScanScheduler(interval_minutes=999)
        assert sched.interval == 999 * 60
        assert sched._task is None
        assert sched._running is False

    def test_scheduler_start_stop(self):
        from api.scheduler import ScanScheduler
        sched = ScanScheduler(interval_minutes=999)

        async def run():
            await sched.start()
            assert sched._running is True
            assert sched._task is not None
            await sched.stop()
            assert sched._running is False

        asyncio.run(run())

    def test_scheduler_interval_env(self, monkeypatch):
        monkeypatch.setenv("RASTRO_SCAN_INTERVAL", "60")
        from api.scheduler import ScanScheduler
        sched = ScanScheduler(interval_minutes=int(__import__("os").environ.get("RASTRO_SCAN_INTERVAL", "30")))
        assert sched.interval == 60 * 60

    def test_scheduler_default_interval(self):
        from api.scheduler import ScanScheduler
        sched = ScanScheduler()
        assert sched.interval == 30 * 60

    def test_scheduler_start_is_idempotent(self):
        from api.scheduler import ScanScheduler
        sched = ScanScheduler(interval_minutes=999)

        async def run():
            await sched.start()
            was_running = sched._running
            await sched.start()
            assert was_running is True
            assert sched._running is True
            await sched.stop()
            assert sched._running is False

        asyncio.run(run())
