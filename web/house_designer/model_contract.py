from __future__ import annotations

from collections import defaultdict
from typing import Any


class ModelValidationError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ModelValidationError(message)


def validate_model(model: dict[str, Any]) -> None:
    _require(isinstance(model, dict), "model must be an object")
    _require(isinstance(model.get("version"), int), "version must be an integer")

    client = model.get("client")
    _require(isinstance(client, dict), "client must be an object")
    _require(bool(client.get("id")), "client.id is required")
    _require(bool(client.get("name")), "client.name is required")

    properties = model.get("properties")
    _require(isinstance(properties, list) and properties, "properties must be a non-empty array")

    for p_idx, prop in enumerate(properties):
        _require(bool(prop.get("id")), f"properties[{p_idx}].id is required")
        _require(bool(prop.get("label")), f"properties[{p_idx}].label is required")
        subjects = prop.get("subjects")
        _require(isinstance(subjects, list) and subjects, f"properties[{p_idx}].subjects must be non-empty")

        for s_idx, subject in enumerate(subjects):
            _require(bool(subject.get("id")), f"subject id missing at properties[{p_idx}].subjects[{s_idx}]")
            floors = subject.get("floors")
            _require(isinstance(floors, list) and floors, f"floors missing at properties[{p_idx}].subjects[{s_idx}]")

            for f_idx, floor in enumerate(floors):
                rooms = floor.get("rooms")
                _require(
                    isinstance(rooms, list) and rooms,
                    f"rooms missing at properties[{p_idx}].subjects[{s_idx}].floors[{f_idx}]",
                )

                for r_idx, room in enumerate(rooms):
                    units = room.get("units", [])
                    _require(
                        isinstance(units, list),
                        f"units must be array at properties[{p_idx}].subjects[{s_idx}].floors[{f_idx}].rooms[{r_idx}]",
                    )
                    for u_idx, unit in enumerate(units):
                        qty = unit.get("quantity", 1)
                        _require(bool(unit.get("type")), f"unit type missing at room path index {u_idx}")
                        _require(isinstance(qty, int) and qty >= 1, f"unit quantity invalid at room path index {u_idx}")


def generate_parts_list(model: dict[str, Any]) -> list[dict[str, Any]]:
    validate_model(model)
    by_type: dict[str, int] = defaultdict(int)

    for prop in model["properties"]:
        for subject in prop["subjects"]:
            for floor in subject["floors"]:
                for room in floor["rooms"]:
                    for unit in room.get("units", []):
                        by_type[str(unit["type"]).strip().lower()] += int(unit.get("quantity", 1))

    result = [{"part_type": k, "quantity": v} for k, v in sorted(by_type.items())]
    return result
