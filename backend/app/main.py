from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AnyHttpUrl

from .models import CheckResult, HistoryResponse, MonitoredURL
from .monitor import MonitorStore, MonitoringEngine
from .utils import perform_check

app = FastAPI(title="Website Uptime Checker", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

store = MonitorStore(persist_path="monitoring_data.json")
engine = MonitoringEngine(store, checker=perform_check)


@app.on_event("startup")
async def startup_event():
    await engine.start()


@app.on_event("shutdown")
async def shutdown_event():
    await engine.stop()


@app.get("/check", response_model=CheckResult)
async def check(url: AnyHttpUrl = Query(..., description="URL to check")):
    return await perform_check(str(url))


@app.get("/monitor/list", response_model=list[MonitoredURL])
async def list_monitored():
    return store.list_urls()


@app.post("/monitor/add")
async def add_monitored(url: AnyHttpUrl = Query(...)):
    store.add_url(url)
    return {"message": "added", "url": str(url)}


@app.delete("/monitor/remove")
async def remove_monitored(url: AnyHttpUrl = Query(...)):
    store.remove_url(url)
    return {"message": "removed", "url": str(url)}


@app.get("/monitor/history", response_model=HistoryResponse)
async def history(url: AnyHttpUrl = Query(...)):
    history = store.get_history(url)
    if history is None:
        raise HTTPException(status_code=404, detail="URL not monitored")
    return HistoryResponse(url=url, checks=history)


@app.get("/health")
async def health():
    return {"status": "ok"}
