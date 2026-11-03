"""API somente leitura sobre observability_requests; o painel estático consome estes endpoints."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient

from app.metrics import project, series, summarize
from app.settings import mongo_settings

app = FastAPI(title="Delta IA Observability")
_client = None


def load_records(days):
    """Lê os últimos dias; a role do Mongo também deve ser somente leitura."""
    global _client
    uri, db_name = mongo_settings()
    if not uri:
        raise HTTPException(503, "MONGO_URI não configurada")
    _client = _client or MongoClient(uri, serverSelectionTimeoutMS=5000)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        cursor = _client[db_name]["observability_requests"].find({"created_at": {"$gte": since}}, {"_id": 0}).sort("created_at", 1)
        return list(cursor)
    except Exception:
        raise HTTPException(503, "Banco indisponível")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/summary")
def summary(days: int = Query(7, ge=1, le=90)):
    data = summarize(load_records(days))
    return {**data, "days": days, "projection": project(data)}


@app.get("/api/series")
def series_route(days: int = Query(7, ge=1, le=90)):
    return series(load_records(days))


app.mount("/", StaticFiles(directory=Path(__file__).resolve().parents[1] / "static", html=True), name="static")
