import json
import unittest
from decimal import Decimal
from pathlib import Path

from cost import calculate_cost


class CostTests(unittest.TestCase):
    def test_slide_examples(self) -> None:
        examples = json.loads(Path(__file__).with_name("usage-examples.json").read_text())
        for example in examples:
            with self.subTest(example=example["name"]):
                costs = calculate_cost(example["usage"], example["prices_per_million"])
                self.assertEqual(costs["input"], Decimal("0.001"))
                self.assertEqual(costs["total"], Decimal(example["expected_total"]))

    def test_read_only_cache_and_no_cache(self) -> None:
        prices = {"input": "1", "cache_read": "0.1", "output": "5"}
        self.assertEqual(
            calculate_cost({"input_tokens": 1000, "output_tokens": 200}, prices)["total"],
            Decimal("0.002"),
        )
        self.assertEqual(
            calculate_cost({
                "input_tokens": 1000,
                "input_tokens_details": {"cached_tokens": 1000},
                "output_tokens": 200,
            }, prices)["total"],
            Decimal("0.0011"),
        )

    def test_reasoning_is_already_in_output(self) -> None:
        usage = {
            "input_tokens": 0, "output_tokens": 200,
            "output_tokens_details": {"reasoning_tokens": 150},
        }
        self.assertEqual(
            calculate_cost(usage, {"output": "5"})["total"], Decimal("0.001"),
        )

    def test_reject_incomplete_or_impossible_usage(self) -> None:
        examples = [
            {},
            {"input_tokens": 1, "output_tokens": 0,
             "input_tokens_details": {"cached_tokens": 2}},
            {"input_tokens": -1, "output_tokens": 0},
            {"input_tokens": True, "output_tokens": 0},
            {"input_tokens": 1, "output_tokens": 0,
             "input_tokens_details": {
                 "cache_write_tokens": 1,
                 "cache_write_tokens_details": {"ttl_30m_tokens": 0, "ttl_12h_tokens": 0},
             }},
        ]
        for usage in examples:
            with self.subTest(usage=usage), self.assertRaises(ValueError):
                calculate_cost(usage, {})

    def test_write_price_must_be_explicit(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing price for cache_write"):
            calculate_cost(
                {"input_tokens": 1, "output_tokens": 0,
                 "input_tokens_details": {"cache_write_tokens": 1}},
                {"input": "1", "output": "5"},
            )

    def test_reject_invalid_prices(self) -> None:
        for price in ["-1", "NaN", "Infinity", "oops"]:
            with self.subTest(price=price), self.assertRaises(ValueError):
                calculate_cost({"input_tokens": 1, "output_tokens": 0}, {"input": price})


if __name__ == "__main__":
    unittest.main()
