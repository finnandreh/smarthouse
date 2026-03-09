# AI Services (Phase 12 Runnable Baseline)

Purpose:
- Provide optimization and prediction services on top of telemetry and configuration data.

Implemented baseline:
- FastAPI AI advisory service at `:8090`.
- `GET /health` for readiness and advisory-mode posture.
- `POST /optimize/validate` for request contract checks.
- `POST /optimize/plan` for deterministic optimization recommendations.

Verification:
- `scripts/verify_ai_service.sh`

Next hardening pass:
- Add model versioning and explainability metadata in response contracts.
- Add offline inference fallback profiles for degraded environments.
