from datetime import datetime, timezone
from typing import List, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="SmartHouse AI Service", version="0.1.0")


class OptimizationRequest(BaseModel):
    project_id: str = Field(min_length=1)
    objective: Literal["energy", "comfort", "cost"]
    horizon_hours: int = Field(ge=1, le=72)
    signals: List[str] = Field(default_factory=list)


class ValidationResponse(BaseModel):
    valid: bool
    errors: List[str]


class OptimizationPlan(BaseModel):
    project_id: str
    objective: str
    generated_at: str
    recommendations: List[str]


def _validate(payload: OptimizationRequest) -> List[str]:
    errors: List[str] = []

    if payload.objective == "energy" and "power_price" not in payload.signals:
        errors.append("objective_energy_requires_signal:power_price")
    if payload.objective == "comfort" and "occupancy" not in payload.signals:
        errors.append("objective_comfort_requires_signal:occupancy")

    return errors


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai", "advisory_mode": True}


@app.post("/optimize/validate", response_model=ValidationResponse)
def validate(payload: OptimizationRequest):
    errors = _validate(payload)
    return ValidationResponse(valid=len(errors) == 0, errors=errors)


@app.post("/optimize/plan", response_model=OptimizationPlan)
def plan(payload: OptimizationRequest):
    errors = _validate(payload)
    if errors:
        raise HTTPException(status_code=422, detail={"code": "INVALID_OPTIMIZATION_REQUEST", "errors": errors})

    recommendations = [
        f"optimize:{payload.objective}:hourly-window={payload.horizon_hours}",
        "preserve_local_control_paths",
    ]

    return OptimizationPlan(
        project_id=payload.project_id,
        objective=payload.objective,
        generated_at=datetime.now(timezone.utc).isoformat(),
        recommendations=recommendations,
    )
