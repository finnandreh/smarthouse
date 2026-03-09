from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="SmartHouse Observability API", version="0.1.0")


class TargetValidationRequest(BaseModel):
    environment: str = Field(min_length=1)
    scrape_targets: List[str] = Field(min_length=1)


class ValidationResponse(BaseModel):
    valid: bool
    errors: List[str]


class DashboardPreviewResponse(BaseModel):
    environment: str
    generated_at: str
    panels: List[str]


def _validate(payload: TargetValidationRequest) -> List[str]:
    errors: List[str] = []
    if "edge-controller" not in payload.scrape_targets:
        errors.append("missing_required_target:edge-controller")
    if "device-registry" not in payload.scrape_targets:
        errors.append("missing_required_target:device-registry")
    return errors


@app.get("/health")
def health():
    return {"status": "ok", "service": "observability-api", "phase": 15}


@app.post("/targets/validate", response_model=ValidationResponse)
def validate_targets(payload: TargetValidationRequest):
    errors = _validate(payload)
    return ValidationResponse(valid=len(errors) == 0, errors=errors)


@app.post("/dashboards/preview", response_model=DashboardPreviewResponse)
def preview_dashboards(payload: TargetValidationRequest):
    errors = _validate(payload)
    if errors:
        raise HTTPException(status_code=422, detail={"code": "INVALID_OBSERVABILITY_TARGETS", "errors": errors})

    panels = [
        "service_health_overview",
        "edge_reconcile_drift_ratio",
        "mqtt_security_events",
    ]

    return DashboardPreviewResponse(
        environment=payload.environment,
        generated_at=datetime.now(timezone.utc).isoformat(),
        panels=panels,
    )
