from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.optimizer import BatteryConfig, TelemetryPoint, optimise_schedule
from app.store import Store

app = FastAPI(title="Energy Flex Orchestrator", version="1.0.0")
store = Store()


class Telemetry(BaseModel):
    timestamp: str
    spot_price_sek_per_kwh: float = Field(ge=0)
    base_load_kwh: float = Field(ge=0)
    solar_generation_kwh: float = Field(ge=0)


class TelemetryBatch(BaseModel):
    asset_id: str = Field(min_length=1)
    points: list[Telemetry] = Field(min_length=1)


class OptimisationRequest(TelemetryBatch):
    battery: BatteryConfig = BatteryConfig()


@app.get("/health")
def health():
    return {"status": "ok", "service": "energy-flex-orchestrator"}


@app.post("/telemetry", status_code=201)
def ingest_telemetry(batch: TelemetryBatch):
    points = [point.model_dump() for point in batch.points]
    store.upsert_telemetry(batch.asset_id, points)
    return {"asset_id": batch.asset_id, "stored_points": len(points)}


@app.get("/assets/{asset_id}/telemetry")
def asset_telemetry(asset_id: str):
    return {"asset_id": asset_id, "points": store.get_telemetry(asset_id)}


@app.post("/plans", status_code=201)
def create_plan(request: OptimisationRequest):
    try:
        result = optimise_schedule(
            [TelemetryPoint(**point.model_dump()) for point in request.points], request.battery
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    plan_id = store.save_plan(request.asset_id, result)
    return {"plan_id": plan_id, "asset_id": request.asset_id, **result}


@app.get("/plans/{plan_id}")
def get_plan(plan_id: int):
    plan = store.get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan
