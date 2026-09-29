"""FastAPI application for the PartnerSignal demo."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .logic import outreach
from .store import complete_follow_up, get_partner, initialize, list_partners


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize()
    yield


app = FastAPI(title="PartnerSignal", version="0.1.0", lifespan=lifespan)
WEB_DIRECTORY = Path(__file__).with_name("web")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(WEB_DIRECTORY / "index.html")


@app.get("/assets/{asset}", include_in_schema=False)
def asset(asset: str) -> FileResponse:
    path = WEB_DIRECTORY / asset
    if not path.is_file() or path.parent != WEB_DIRECTORY:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return FileResponse(path)


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"status": "ok", "service": "partner-signal", "data": "fictional demo data"}


@app.get("/api/overview")
def overview() -> dict[str, object]:
    partners = list_partners()
    stages = {stage: sum(partner["stage"] == stage for partner in partners) for stage in {p["stage"] for p in partners}}
    services = {}
    for partner in partners:
        service = partner["recommended_service"]
        services[service] = services.get(service, 0) + 1
    return {
        "partners": len(partners),
        "qualified": sum(partner["stage"] in {"Qualified", "Technical review", "Proposal"} for partner in partners),
        "follow_ups_due": sum(not partner["follow_up_complete"] for partner in partners),
        "average_score": round(sum(partner["opportunity_score"] for partner in partners) / len(partners)),
        "stages": stages,
        "services": services,
    }


@app.get("/api/partners")
def partners() -> list[dict[str, object]]:
    return list_partners()


@app.get("/api/partners/{partner_id}")
def partner(partner_id: str) -> dict[str, object]:
    result = get_partner(partner_id)
    if not result:
        raise HTTPException(status_code=404, detail="Partner not found.")
    return result


@app.get("/api/partners/{partner_id}/outreach")
def partner_outreach(partner_id: str) -> dict[str, str]:
    result = get_partner(partner_id)
    if not result:
        raise HTTPException(status_code=404, detail="Partner not found.")
    return outreach(result)


@app.post("/api/partners/{partner_id}/complete-follow-up")
def partner_follow_up(partner_id: str) -> dict[str, object]:
    result = complete_follow_up(partner_id)
    if not result:
        raise HTTPException(status_code=404, detail="Partner not found.")
    return result
