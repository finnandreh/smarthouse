# Telemetry Pipeline (Phase 11 Runnable Baseline)

Purpose:
- Ingest, normalize, and route telemetry for storage and analytics.

Implemented baseline:
- FastAPI telemetry service at `:8089`.
- `GET /health` for readiness and local retention posture.
- `POST /ingest/validate` for contract/schema validation.
- `POST /ingest/batch` for deterministic ingest acknowledgements.
- Writer abstraction with `TELEMETRY_WRITER` (`inmemory` or `postgres_stub`).
- Retention placeholders via `TELEMETRY_RETENTION_HOURS` and `POST /retention/run`.

Verification:
- `scripts/verify_telemetry.sh`

Next hardening pass:
- Add durable local buffering with backpressure controls.
- Add pluggable TSDB writer contracts and retention windows.
