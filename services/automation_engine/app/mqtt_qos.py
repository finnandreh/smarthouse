import os

_KIND_ENV = {
    "telemetry": "MQTT_QOS_TELEMETRY",
    "control": "MQTT_QOS_CONTROL",
    "status": "MQTT_QOS_STATUS",
    "event": "MQTT_QOS_EVENT",
    "config": "MQTT_QOS_CONFIG",
}

_KIND_DEFAULT = {
    "telemetry": 0,
    "control": 1,
    "status": 1,
    "event": 1,
    "config": 1,
}


def _read_qos(env_name: str, default: int) -> int:
    raw = os.getenv(env_name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    if value < 0 or value > 2:
        return default
    return value


def qos_for_kind(kind: str, critical: bool = False) -> int:
    normalized = kind.lower().strip()
    default = _KIND_DEFAULT.get(normalized, 1)
    env_name = _KIND_ENV.get(normalized)
    if env_name:
        qos = _read_qos(env_name, default)
    else:
        qos = default

    if normalized == "event" and critical:
        return _read_qos("MQTT_QOS_EVENT_CRITICAL", 2)

    return qos
