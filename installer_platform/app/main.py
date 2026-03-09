from datetime import datetime, timezone
from typing import List, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="SmartHouse Installer Platform", version="0.1.0")

SUPPORTED_TARGETS = {"edge-controller", "edge-controller-ha"}
SUPPORTED_CHANNELS = {"stable", "candidate"}


class InstallRequest(BaseModel):
    site_id: str = Field(min_length=1)
    installer_id: str = Field(min_length=1)
    target: Literal["edge-controller", "edge-controller-ha"]
    package_version: str = Field(min_length=1)
    channel: Literal["stable", "candidate"] = "stable"
    include_steps: List[str] = Field(default_factory=list)


class InstallValidationResponse(BaseModel):
    valid: bool
    errors: List[str]


class InstallPlanResponse(BaseModel):
    site_id: str
    installer_id: str
    target: str
    package_version: str
    channel: str
    generated_at: str
    steps: List[str]


def _validate(payload: InstallRequest) -> List[str]:
    errors: List[str] = []

    if payload.target not in SUPPORTED_TARGETS:
        errors.append(f"unsupported_target:{payload.target}")

    if payload.channel not in SUPPORTED_CHANNELS:
        errors.append(f"unsupported_channel:{payload.channel}")

    if payload.target == "edge-controller-ha" and "ha-precheck" not in payload.include_steps:
        errors.append("ha_target_requires_step:ha-precheck")

    return errors


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "installer-platform",
        "local_first": True,
    }


@app.post("/install/validate", response_model=InstallValidationResponse)
def validate_install(payload: InstallRequest):
    errors = _validate(payload)
    return InstallValidationResponse(valid=len(errors) == 0, errors=errors)


@app.post("/install/plan", response_model=InstallPlanResponse)
def build_plan(payload: InstallRequest):
    errors = _validate(payload)
    if errors:
        raise HTTPException(status_code=422, detail={"code": "INVALID_INSTALL_PLAN", "errors": errors})

    steps = payload.include_steps or ["precheck", "package-download", "install", "postcheck"]

    return InstallPlanResponse(
        site_id=payload.site_id,
        installer_id=payload.installer_id,
        target=payload.target,
        package_version=payload.package_version,
        channel=payload.channel,
        generated_at=datetime.now(timezone.utc).isoformat(),
        steps=steps,
    )
