from typing import Tuple

TOPIC_PREFIX = "platform"
ALLOWED_KINDS = {"status", "telemetry", "control", "event", "config"}


def build_topic(house: str, device_id: str, kind: str) -> str:
    if kind not in ALLOWED_KINDS:
        raise ValueError(f"Unsupported topic kind: {kind}")
    return f"{TOPIC_PREFIX}/{house}/{device_id}/{kind}"


def parse_topic(topic: str) -> Tuple[str, str, str]:
    parts = topic.split("/")
    if len(parts) != 4:
        raise ValueError(f"Unexpected topic format: {topic}")
    prefix, house, device_id, kind = parts
    if prefix != TOPIC_PREFIX:
        raise ValueError(f"Unexpected topic prefix: {prefix}")
    if kind not in ALLOWED_KINDS:
        raise ValueError(f"Unsupported topic kind: {kind}")
    return house, device_id, kind
