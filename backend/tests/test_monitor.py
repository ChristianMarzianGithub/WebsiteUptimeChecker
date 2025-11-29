import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.models import CheckResult
from app.monitor import MonitorStore, MonitoringEngine


@pytest.mark.asyncio
async def test_store_limits_history():
    store = MonitorStore()
    for i in range(25):
        store.record_result(
            "https://example.com",
            CheckResult(
                status_code=200,
                status_text="UP",
                response_time_ms=100,
                final_url="https://example.com",
                redirect_chain=["https://example.com"],
                ssl=None,
                dns=None,
                timestamp=datetime.now(timezone.utc),
            ),
        )
    assert len(store.get_history("https://example.com")) == 20


@pytest.mark.asyncio
async def test_engine_runs_checks_and_alerts():
    calls = []

    async def fake_checker(url):
        calls.append(url)
        return CheckResult(
            status_code=500,
            status_text="DOWN" if len(calls) == 1 else "UP",
            response_time_ms=200,
            final_url=url,
            redirect_chain=[url],
            ssl=None,
            dns=None,
            timestamp=datetime.now(timezone.utc),
        )

    store = MonitorStore()
    store.add_url("https://example.com")
    engine = MonitoringEngine(store, checker=fake_checker, interval_seconds=1)

    await engine.run_once()
    await engine.run_once()
    history = store.get_history("https://example.com")
    assert len(history) == 2
    assert history[-1].status_text == "UP"
