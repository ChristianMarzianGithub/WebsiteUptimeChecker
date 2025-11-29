import asyncio
import contextlib
import json
import os
from typing import Dict, List, Optional

from pydantic import HttpUrl

from .models import CheckResult, MonitoredURL


class MonitorStore:
    def __init__(self, persist_path: str | None = None):
        self.persist_path = persist_path
        self.monitored: Dict[str, List[CheckResult]] = {}
        if self.persist_path and os.path.exists(self.persist_path):
            self._load()

    def _load(self) -> None:
        with open(self.persist_path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        for url, items in raw.items():
            self.monitored[url] = [CheckResult(**entry) for entry in items]

    def _persist(self) -> None:
        if not self.persist_path:
            return
        data = {url: [item.model_dump(mode="json") for item in history] for url, history in self.monitored.items()}
        with open(self.persist_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, default=str, indent=2)

    def add_url(self, url: HttpUrl) -> None:
        if str(url) not in self.monitored:
            self.monitored[str(url)] = []
            self._persist()

    def remove_url(self, url: HttpUrl) -> None:
        if str(url) in self.monitored:
            self.monitored.pop(str(url))
            self._persist()

    def record_result(self, url: HttpUrl, result: CheckResult) -> None:
        history = self.monitored.setdefault(str(url), [])
        history.append(result)
        if len(history) > 20:
            self.monitored[str(url)] = history[-20:]
        self._persist()

    def list_urls(self) -> List[MonitoredURL]:
        entries: List[MonitoredURL] = []
        for url, history in self.monitored.items():
            last = history[-1] if history else None
            uptime = None
            if history:
                up_count = sum(1 for item in history if item.status_text == "UP")
                uptime = round((up_count / len(history)) * 100, 2)
            entries.append(
                MonitoredURL(
                    url=url,
                    last_status=last.status_text if last else None,
                    last_response_time=last.response_time_ms if last else None,
                    uptime_percentage=uptime,
                )
            )
        return entries

    def get_history(self, url: HttpUrl) -> List[CheckResult]:
        return self.monitored.get(str(url), [])


class MonitoringEngine:
    def __init__(self, store: MonitorStore, checker, interval_seconds: int = 60):
        self.store = store
        self.checker = checker
        self.interval_seconds = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self.alert_webhook = os.getenv("ALERT_WEBHOOK_URL")

    async def start(self) -> None:
        if not self._task:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self.interval_seconds)

    async def run_once(self) -> None:
        for url in list(self.store.monitored.keys()):
            result = await self.checker(url)
            previous = self.store.get_history(url)[-1] if self.store.get_history(url) else None
            self.store.record_result(url, result)
            await self._maybe_send_alert(url, previous, result)

    async def _maybe_send_alert(self, url: str, previous: Optional[CheckResult], current: CheckResult) -> None:
        if not self.alert_webhook:
            return
        became_down = previous and previous.status_text == "UP" and current.status_text == "DOWN"
        became_up = previous and previous.status_text == "DOWN" and current.status_text == "UP"
        first_status = previous is None and current.status_text in {"UP", "DOWN"}
        if not (became_down or became_up or first_status):
            return
        payload = {
            "url": url,
            "status": current.status_text,
            "timestamp": current.timestamp.isoformat(),
            "status_code": current.status_code,
        }
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(self.alert_webhook, json=payload)
        except Exception:
            pass


__all__ = ["MonitorStore", "MonitoringEngine"]
