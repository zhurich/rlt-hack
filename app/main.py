"""API и страница подбора поставщиков.

    uvicorn app.main:app --port 8000
"""
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from recsys.service import Service

WEB = Path(__file__).resolve().parent.parent / "web"

# Цифры качества из docs/metrics.md и docs/enrichment.md — показываются в подвале страницы.
QUALITY = {
    "recall10": 0.656, "winner10": 0.671, "map10": 0.447, "test_lots": 5923,
    "baseline_okpd": 0.397, "baseline_popular": 0.048,
    "sources": [
        "История закупок АИС ГЗ и электронного магазина СПб, 2024–2025",
        "Единый реестр субъектов МСП (ФНС), 10.09.2026",
        "Среднесписочная численность, доходы и расходы, задолженность (ФНС), 25.09.2026",
        "Реестр недобросовестных поставщиков (ЕИС), 01.10.2026",
    ],
}

# Кейсы для защиты (docs/defense.md), все — из отложенного периода ноября–декабря 2025.
DEMO_LOTS = [5964926, 6038385, 5953570, 6026673, 5959879, 6019464, 5954657]

state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    state["svc"] = Service()
    state["examples"] = state["svc"].examples(DEMO_LOTS)
    state["stats"] = {**state["svc"].stats(), **QUALITY}
    yield


app = FastAPI(title="Подбор поставщиков", lifespan=lifespan)


class NewPurchase(BaseModel):
    text: str
    codes: list[str] = []
    price: float | None = None
    customer_inn: str | None = None
    source: str | None = None
    is_smp: bool = False


def timed(result: dict, t0: float) -> dict:
    result["elapsed_ms"] = round((time.time() - t0) * 1000)
    return result


@app.get("/api/lot/{lot_id}")
def by_lot(lot_id: int):
    t0 = time.time()
    result = state["svc"].by_lot(lot_id)
    if result is None:
        raise HTTPException(404, f"Лот {lot_id} не найден")
    return timed(result, t0)


@app.post("/api/recommend")
def by_input(p: NewPurchase):
    if not p.text.strip() and not p.codes:
        raise HTTPException(400, "Укажите предмет закупки или коды ОКПД2")
    t0 = time.time()
    return timed(state["svc"].by_input(p.text, p.codes, p.price, p.customer_inn or None, p.source or None, p.is_smp), t0)


@app.get("/api/search")
def search(q: str):
    return state["svc"].search_lots(q)


@app.get("/api/examples")
def examples():
    return state["examples"]


@app.get("/api/stats")
def stats():
    return state["stats"]


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")
