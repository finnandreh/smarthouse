from datetime import datetime, timezone
from typing import Dict, List, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="SmartHouse Project Engine", version="0.1.0")


class PlannedDevice(BaseModel):
    device_id: str = Field(min_length=1)
    device_type: str = Field(min_length=1)
    protocol: Literal["wifi", "ethernet", "modbus", "knx", "bacnet"]
    capabilities: List[str] = Field(default_factory=list)


class ZoneDefinition(BaseModel):
    zone_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    devices: List[PlannedDevice] = Field(default_factory=list)


class ProjectCreateRequest(BaseModel):
    house_id: str = Field(min_length=1)
    project_name: str = Field(min_length=1)
    zones: List[ZoneDefinition] = Field(default_factory=list)


class ProjectRecord(BaseModel):
    project_id: str
    house_id: str
    project_name: str
    zones: List[ZoneDefinition]
    revision: int
    created_at: str
    updated_at: str


class GenerationContract(BaseModel):
    project_id: str
    contract_version: str
    generated_at: str
    devices_by_protocol: Dict[str, List[PlannedDevice]]
    zone_count: int


_PROJECTS: Dict[str, ProjectRecord] = {}
_DEVICE_CAPABILITY_POLICY: Dict[str, set[str]] = {
    "relay_module": {"relay_output", "power_monitor", "diagnostics"},
    "dimmer_module": {"dimmer_output", "power_monitor", "diagnostics"},
    "thermostat": {"temperature_sensor", "hvac_mode", "setpoint_control", "battery_level"},
    "sensor_node": {"motion_sensor", "temperature_sensor", "humidity_sensor", "battery_level"},
}


class ProjectValidationResult(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _group_devices_by_protocol(zones: List[ZoneDefinition]) -> Dict[str, List[PlannedDevice]]:
    grouped: Dict[str, List[PlannedDevice]] = {}
    for zone in zones:
        for device in zone.devices:
            grouped.setdefault(device.protocol, []).append(device)
    return grouped


def _validate_project_payload(payload: ProjectCreateRequest) -> List[str]:
    errors: List[str] = []
    for zone in payload.zones:
        for device in zone.devices:
            policy = _DEVICE_CAPABILITY_POLICY.get(device.device_type)
            if policy is None:
                errors.append(
                    f"zone={zone.zone_id} device={device.device_id} unsupported_device_type={device.device_type}"
                )
                continue

            unsupported = [cap for cap in device.capabilities if cap not in policy]
            if unsupported:
                errors.append(
                    f"zone={zone.zone_id} device={device.device_id} unsupported_capabilities={','.join(unsupported)}"
                )

    return errors


@app.get("/health")
def health():
    return {"status": "ok", "service": "project-engine"}


@app.post("/projects", response_model=ProjectRecord)
def create_project(payload: ProjectCreateRequest):
    validation_errors = _validate_project_payload(payload)
    if validation_errors:
        raise HTTPException(
            status_code=422,
            detail={"code": "PROJECT_VALIDATION_FAILED", "errors": validation_errors},
        )

    project_id = str(uuid4())
    now = _now_iso()
    record = ProjectRecord(
        project_id=project_id,
        house_id=payload.house_id,
        project_name=payload.project_name,
        zones=payload.zones,
        revision=1,
        created_at=now,
        updated_at=now,
    )
    _PROJECTS[project_id] = record
    return record


@app.post("/projects/validate", response_model=ProjectValidationResult)
def validate_project(payload: ProjectCreateRequest):
    errors = _validate_project_payload(payload)
    return ProjectValidationResult(valid=not errors, errors=errors)


@app.get("/projects")
def list_projects():
    return {"items": list(_PROJECTS.values())}


@app.get("/projects/{project_id}", response_model=ProjectRecord)
def get_project(project_id: str):
    if project_id not in _PROJECTS:
        raise HTTPException(status_code=404, detail="Project not found")
    return _PROJECTS[project_id]


@app.get("/projects/{project_id}/generation-contract", response_model=GenerationContract)
def project_generation_contract(project_id: str):
    if project_id not in _PROJECTS:
        raise HTTPException(status_code=404, detail="Project not found")

    project = _PROJECTS[project_id]
    grouped = _group_devices_by_protocol(project.zones)
    return GenerationContract(
        project_id=project.project_id,
        contract_version="phase7-v1",
        generated_at=_now_iso(),
        devices_by_protocol=grouped,
        zone_count=len(project.zones),
    )
