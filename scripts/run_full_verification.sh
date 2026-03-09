#!/usr/bin/env bash
set -euo pipefail

cd /mnt/c/smarthouse

chmod +x scripts/generate_mqtt_tls_certs.sh
chmod +x scripts/issue_client_cert.sh
chmod +x scripts/revoke_client_cert.sh
chmod +x scripts/rotate_service_certs.sh
chmod +x scripts/verify_mqtt_auth.sh
chmod +x scripts/verify_revocation.sh
chmod +x scripts/verify_acl_enforcement.sh
chmod +x scripts/verify_plaintext_disabled.sh
chmod +x scripts/smoke_test_e2e.sh
chmod +x scripts/verify_persistence.sh
chmod +x scripts/verify_auth_and_bridges.sh
chmod +x scripts/verify_bridge_mqtt_flow.sh
chmod +x scripts/auth_token.sh
chmod +x scripts/verify_auth_security_controls.sh
chmod +x scripts/verify_jwt_kid_rotation.sh
chmod +x scripts/prune_revoked_tokens.sh
chmod +x scripts/verify_revoked_token_prune.sh
chmod +x scripts/verify_edge_controller.sh
chmod +x scripts/verify_edge_maintenance_recovery.sh
chmod +x scripts/verify_project_engine.sh
chmod +x scripts/verify_system_generator.sh
chmod +x scripts/verify_cloud_services.sh
chmod +x scripts/verify_installer_platform.sh
chmod +x scripts/verify_telemetry.sh
chmod +x scripts/verify_ai_service.sh
chmod +x scripts/verify_observability.sh
chmod +x scripts/verify_system_tests.sh
chmod +x scripts/verify_phase_scaffold_integrity.sh
chmod +x scripts/verify_device_sdk.sh
chmod +x scripts/verify_device_sdk_unit.sh
chmod +x scripts/verify_device_sdk_bootstrap.sh
chmod +x scripts/verify_device_sdk_mqtt_integration.sh

scripts/generate_mqtt_tls_certs.sh
docker compose down
docker compose up -d --build --force-recreate

scripts/verify_mqtt_auth.sh
scripts/verify_revocation.sh
scripts/verify_acl_enforcement.sh
scripts/verify_plaintext_disabled.sh
scripts/smoke_test_e2e.sh
scripts/verify_persistence.sh
scripts/verify_auth_and_bridges.sh
scripts/verify_auth_security_controls.sh
scripts/verify_jwt_kid_rotation.sh
scripts/verify_revoked_token_prune.sh
scripts/verify_edge_controller.sh
scripts/verify_edge_maintenance_recovery.sh
scripts/verify_project_engine.sh
scripts/verify_system_generator.sh
scripts/verify_cloud_services.sh
scripts/verify_installer_platform.sh
scripts/verify_telemetry.sh
scripts/verify_ai_service.sh
scripts/verify_observability.sh
scripts/verify_phase_scaffold_integrity.sh
scripts/verify_system_tests.sh
scripts/verify_device_sdk.sh
scripts/verify_device_sdk_unit.sh
scripts/verify_device_sdk_bootstrap.sh
scripts/verify_device_sdk_mqtt_integration.sh
scripts/verify_bridge_mqtt_flow.sh

echo "FULL_VERIFICATION=passed"
