import json
import unittest
from pathlib import Path

from web.house_designer.model_contract import generate_parts_list, validate_model


class HouseDesignerContractsTests(unittest.TestCase):
    def test_demo_config_validates(self) -> None:
        data = json.loads(Path("examples/house_designer/client_demo.json").read_text(encoding="utf-8"))
        validate_model(data)

    def test_parts_list_generation(self) -> None:
        data = json.loads(Path("examples/house_designer/client_demo.json").read_text(encoding="utf-8"))
        parts = generate_parts_list(data)
        indexed = {item["part_type"]: item["quantity"] for item in parts}
        self.assertEqual(indexed.get("light"), 6)
        self.assertEqual(indexed.get("outlet"), 8)
        self.assertEqual(indexed.get("tempsensor"), 1)


if __name__ == "__main__":
    unittest.main()
