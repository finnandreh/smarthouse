from datetime import datetime, timezone
from typing import List, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="SmartHouse Cloud Services", version="0.1.0")


class SyncPreviewRequest(BaseModel):
    site_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    mode: Literal["metadata-only", "telemetry-summary"] = "metadata-only"
    include_sections: List[str] = Field(default_factory=list)


class SyncPreviewResponse(BaseModel):
    site_id: str
    tenant_id: str
    mode: str
    prepared_at: str
    sections: List[str]
    estimated_records: int


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "cloud-services",
        "cloud_optional": True,
        "local_first_core_unchanged": True,
    }


@app.post("/sync/preview", response_model=SyncPreviewResponse)
def sync_preview(payload: SyncPreviewRequest):
    if payload.mode == "telemetry-summary" and "telemetry" not in payload.include_sections:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_SYNC_REQUEST",
                "reason": "telemetry-summary mode requires telemetry section",
            },
        )

    sections = payload.include_sections or ["devices", "automation", "configuration"]
    estimated_records = max(1, len(sections) * 25)

    return SyncPreviewResponse(
        site_id=payload.site_id,
        tenant_id=payload.tenant_id,
        mode=payload.mode,
        prepared_at=datetime.now(timezone.utc).isoformat(),
        sections=sections,
        estimated_records=estimated_records,
    )
