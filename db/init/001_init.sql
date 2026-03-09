CREATE TABLE IF NOT EXISTS devices (
  id TEXT PRIMARY KEY,
  house TEXT NOT NULL,
  type TEXT NOT NULL,
  protocol TEXT NOT NULL,
  capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS registry_events (
  event_id BIGSERIAL PRIMARY KEY,
  device_id TEXT NOT NULL,
  house TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS automation_events (
  event_id BIGSERIAL PRIMARY KEY,
  house TEXT NOT NULL,
  device_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS automation_actions (
  action_id BIGSERIAL PRIMARY KEY,
  house TEXT NOT NULL,
  device_id TEXT NOT NULL,
  action JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS automation_dead_letters (
  dead_letter_id BIGSERIAL PRIMARY KEY,
  topic TEXT NOT NULL,
  raw_payload TEXT NOT NULL,
  reason TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS provisioning_audit (
  audit_id BIGSERIAL PRIMARY KEY,
  subject TEXT NOT NULL,
  house TEXT NOT NULL,
  role TEXT NOT NULL,
  scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
  issued_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auth_security_events (
  event_id BIGSERIAL PRIMARY KEY,
  service_name TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  client_ip TEXT NOT NULL,
  subject TEXT,
  outcome TEXT NOT NULL,
  reason TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS revoked_tokens (
  jti TEXT PRIMARY KEY,
  subject TEXT,
  revoked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS edge_controller_audit (
  audit_id BIGSERIAL PRIMARY KEY,
  endpoint TEXT NOT NULL,
  action TEXT NOT NULL,
  actor TEXT,
  scope TEXT,
  outcome TEXT NOT NULL,
  reason TEXT NOT NULL,
  client_ip TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS edge_idempotency_keys (
  endpoint TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  request_hash TEXT NOT NULL,
  response JSONB,
  status_code INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (endpoint, idempotency_key)
);
