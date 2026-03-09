from fastapi import FastAPI
from pydantic import BaseModel

from bridge_common.adapter_base import BridgeAdapterBase


class EmitRequest(BaseModel):
    event: str
    value: float | int | str | bool


app = FastAPI(title="SmartHouse BACnet Bridge", version="0.1.0")
adapter = BridgeAdapterBase("bacnet")


@app.on_event("startup")
def startup_event():
    adapter.connect()


@app.on_event("shutdown")
def shutdown_event():
    adapter.close()


@app.get("/health")
def health():
    return {"status": "ok", "bridge": "bacnet", "protocol": adapter.protocol}


@app.post("/emit-test")
def emit_test(payload: EmitRequest):
    adapter.publish_event(payload.model_dump())
    return {"published": True, "bridge": "bacnet"}


@app.post("/lifecycle/reload")
def lifecycle_reload():
    adapter.close()
    adapter.connect()
    return {"reloaded": True, "bridge": "bacnet"}


@app.post("/lifecycle/restart")
def lifecycle_restart():
    adapter.close()
    adapter.connect()
    return {"restarted": True, "bridge": "bacnet"}
