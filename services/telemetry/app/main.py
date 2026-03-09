from datetime import datetime, timezone
from math import isfinite
from typing import List, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="SmartHouse Telemetry Service", version="0.1.0")


class MetricPoint(BaseModel):
    name: str = Field(min_length=1)
    value: float
    unit: str = Field(min_length=1)


class IngestRequest(BaseModel):
    house_id: str = Field(min_length=1)
    source_protocol: Literal["mqtt", "modbus", "knx", "bacnet"]
    points: List[MetricPoint] = Field(min_length=1)


class ValidateResponse(BaseModel):
    valid: bool
    errors: List[str]


class IngestResponse(BaseModel):
    accepted: bool
    house_id: str
    source_protocol: str
    point_count: int
    received_at: str


def _validate(payload: IngestRequest) -> List[str]:
    errors: List[str] = []
    for index, point in enumerate(payload.points):
        if not isfinite(point.value):
            errors.append(f"point[{index}].value_not_finite")
        if point.name.startswith("debug_"):
            errors.append(f"point[{index}].disallowed_metric_name")
    return errors


@app.get("/health")
def health():
    return {"status": "ok", "service": "telemetry", "local_retention": True}


@app.post("/ingest/validate", response_model=ValidateResponse)
def validate(payload: IngestRequest):
    errors = _validate(payload)
    return ValidateResponse(valid=len(errors) == 0, errors=errors)


@app.post("/ingest/batch", response_model=IngestResponse)
def ingest_batch(payload: IngestRequest):
    errors = _validate(payload)
    if errors:
        raise HTTPException(status_code=422, detail={"code": "INVALID_TELEMETRY_BATCH", "errors": errors})

    return IngestResponse(
        accepted=True,
        house_id=payload.house_id,
        source_protocol=payload.source_protocol,
        point_count=len(payload.points),
        received_at=datetime.now(timezone.utc).isoformat(),
    )
