# Cloud Services (Phase 10 Runnable Baseline)

Purpose:
- Host optional remote management, notifications, and analytics integrations.
- Preserve local-first operation by keeping cloud features opt-in.

Implemented baseline:
- FastAPI service at `:8087`.
- `GET /health` for service and local-first posture checks.
- `POST /sync/preview` for preflight sync estimation and contract validation.

Verification:
- `scripts/verify_cloud_services.sh`

Next hardening pass:
- Add tenant-isolation auth boundaries.
- Add signed sync jobs and command relay audit trails.
