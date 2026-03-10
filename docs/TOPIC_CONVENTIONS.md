# MQTT Topic Conventions

Base template:

`platform/{house}/{device}/{kind}`

Allowed kinds:

- `status`
- `telemetry`
- `control`
- `event`
- `config`

Optional shared topic:

- `platform/discovery`

Examples:

- `platform/home01/device123/status`
- `platform/home01/device123/telemetry`
- `platform/home01/device123/control`
- `platform/home01/device123/event`
- `platform/home01/device123/config`

Payloads should be JSON encoded UTF-8.
