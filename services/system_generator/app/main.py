from datetime import datetime, timezone
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="SmartHouse System Generator", version="0.1.0")


class PlannedDevice(BaseModel):
    device_id: str = Field(min_length=1)
    device_type: str = Field(min_length=1)
    protocol: str = Field(min_length=1)
    capabilities: List[str] = Field(default_factory=list)


class GenerationContract(BaseModel):
    project_id: str = Field(min_length=1)
    contract_version: str = Field(min_length=1)
    generated_at: str = Field(min_length=1)
    devices_by_protocol: Dict[str, List[PlannedDevice]] = Field(default_factory=dict)
    zone_count: int = Field(ge=0)


class GenerateRequest(BaseModel):
    contract: GenerationContract
    mode: str = Field(default="dry-run")


class GenerateResponse(BaseModel):
    project_id: str
    generated_at: str
    artifact_plan: Dict[str, object]


SUPPORTED_PROTOCOLS = {"wifi", "ethernet", "modbus", "knx", "bacnet"}


def _validate_contract(contract: GenerationContract) -> List[str]:
    errors: List[str] = []
    if contract.contract_version != "phase7-v1":
        errors.append("unsupported_contract_version")

    for protocol, devices in contract.devices_by_protocol.items():
        if protocol not in SUPPORTED_PROTOCOLS:
            errors.append(f"unsupported_protocol:{protocol}")
        for d in devices:
            if not d.device_id:
                errors.append("missing_device_id")
            if not d.device_type:
                errors.append(f"missing_device_type:{d.device_id}")

    if contract.zone_count < 0:
        errors.append("invalid_zone_count")

    return errors


@app.get("/health")
def health():
    return {"status": "ok", "service": "system-generator"}


@app.post("/validate")
def validate_contract(contract: GenerationContract):
    errors = _validate_contract(contract)
    return {"valid": not errors, "errors": errors}


@app.post("/generate", response_model=GenerateResponse)
def generate(payload: GenerateRequest):
    if payload.mode not in {"dry-run", "plan"}:
        raise HTTPException(status_code=400, detail="Unsupported mode")

    errors = _validate_contract(payload.contract)
    if errors:
        raise HTTPException(status_code=422, detail={"code": "CONTRACT_VALIDATION_FAILED", "errors": errors})

    total_devices = sum(len(v) for v in payload.contract.devices_by_protocol.values())
    artifact_plan = {
        "mode": payload.mode,
        "protocols": sorted(payload.contract.devices_by_protocol.keys()),
        "total_devices": total_devices,
        "zone_count": payload.contract.zone_count,
    }

    return GenerateResponse(
        project_id=payload.contract.project_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        artifact_plan=artifact_plan,
    )
