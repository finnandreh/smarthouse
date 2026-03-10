#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web.house_designer.model_contract import ModelValidationError, generate_parts_list


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate parts list from house designer JSON")
    parser.add_argument("--input", required=True, help="Path to house designer JSON input")
    parser.add_argument("--output", default="", help="Optional output JSON path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    src = Path(args.input)
    data = json.loads(src.read_text(encoding="utf-8"))

    try:
        parts = generate_parts_list(data)
    except ModelValidationError as exc:
        print(f"PARTS_GENERATION=failed reason={exc}")
        return 1

    payload = {
        "client": data.get("client", {}),
        "parts": parts,
        "total_part_types": len(parts),
        "total_quantity": sum(item["quantity"] for item in parts),
    }

    text = json.dumps(payload, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"PARTS_GENERATION=ok output={args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
