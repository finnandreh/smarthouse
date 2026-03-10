import os
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List


@dataclass(frozen=True)
class TelemetryEnvelope:
    house_id: str
    source_protocol: str
    points: List[Dict[str, object]]
    received_at: str


class TelemetryWriterBase:
    def write(self, envelope: TelemetryEnvelope) -> bool:
        raise NotImplementedError

    def prune_older_than(self, cutoff: datetime) -> int:
        raise NotImplementedError


class InMemoryTelemetryWriter(TelemetryWriterBase):
    def __init__(self):
        self._records: List[TelemetryEnvelope] = []
        self._lock = threading.Lock()

    def write(self, envelope: TelemetryEnvelope) -> bool:
        with self._lock:
            self._records.append(envelope)
        return True

    def prune_older_than(self, cutoff: datetime) -> int:
        with self._lock:
            before = len(self._records)
            self._records = [
                item
                for item in self._records
                if datetime.fromisoformat(item.received_at) >= cutoff
            ]
            return before - len(self._records)


class PostgresTelemetryWriterStub(TelemetryWriterBase):
    """Stub writer for interface parity before durable backend implementation."""

    def __init__(self, database_url: str):
        self.database_url = database_url

    def write(self, envelope: TelemetryEnvelope) -> bool:
        _ = envelope
        return True

    def prune_older_than(self, cutoff: datetime) -> int:
        _ = cutoff
        return 0


def writer_mode_from_env() -> str:
    raw = os.getenv("TELEMETRY_WRITER", "inmemory").strip().lower()
    if raw in {"inmemory", "postgres_stub"}:
        return raw
    return "inmemory"


def retention_hours_from_env() -> int:
    raw = os.getenv("TELEMETRY_RETENTION_HOURS", "168").strip()
    try:
        value = int(raw)
    except ValueError:
        return 168
    if value < 1:
        return 1
    return value


def build_writer() -> TelemetryWriterBase:
    mode = writer_mode_from_env()
    if mode == "postgres_stub":
        return PostgresTelemetryWriterStub(database_url=os.getenv("DATABASE_URL", ""))
    return InMemoryTelemetryWriter()


def retention_cutoff(now: datetime, retention_hours: int) -> datetime:
    return now - timedelta(hours=retention_hours)
