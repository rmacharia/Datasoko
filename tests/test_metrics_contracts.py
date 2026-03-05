from __future__ import annotations

import unittest

from backend.metrics.contracts import (
    ContractValidationError,
    UNAVAILABLE,
    build_llm_narration_input,
    validate_llm_output,
    validate_metrics_json,
)


def _valid_metrics() -> dict:
    return {
        "week": {
            "start": "2026-02-23",
            "end": "2026-03-01",
            "previous_start": "2026-02-16",
            "previous_end": "2026-02-22",
        },
        "weekly_revenue": 1500.5,
        "previous_week_revenue": 1200.0,
        "week_over_week_delta_pct": 25.04,
        "top_products": [
            {"product_name": "Milk", "revenue": 700.0, "contribution_pct": 46.65},
            {"product_name": "Bread", "revenue": 400.0, "contribution_pct": 26.66},
        ],
        "slow_movers": [
            {"product_name": "Sugar", "last_sale_date": "2026-02-10", "days_since_last_sale": 19}
        ],
        "repeat_customers": 4,
        "avg_transaction_value": 214.36,
        "meta": {
            "slow_mover_days": 14,
            "top_n_products": 5,
            "records_processed": 23,
        },
    }


class MetricsContractsTests(unittest.TestCase):
    def test_validate_metrics_json_accepts_valid_payload(self) -> None:
        metrics = _valid_metrics()
        validate_metrics_json(metrics)

    def test_validate_metrics_json_rejects_missing_required_key(self) -> None:
        metrics = _valid_metrics()
        del metrics["weekly_revenue"]

        with self.assertRaises(ContractValidationError) as ctx:
            validate_metrics_json(metrics)

        self.assertIn("missing keys", str(ctx.exception))

    def test_validate_metrics_json_rejects_wrong_numeric_type(self) -> None:
        metrics = _valid_metrics()
        metrics["repeat_customers"] = "4"

        with self.assertRaises(ContractValidationError) as ctx:
            validate_metrics_json(metrics)

        self.assertIn("repeat_customers", str(ctx.exception))

    def test_validate_metrics_json_accepts_unavailable_for_optional_numeric_fields(self) -> None:
        metrics = _valid_metrics()
        metrics["week_over_week_delta_pct"] = UNAVAILABLE
        metrics["avg_transaction_value"] = UNAVAILABLE

        validate_metrics_json(metrics)

    def test_validate_metrics_json_rejects_invalid_unavailable_usage(self) -> None:
        metrics = _valid_metrics()
        metrics["week_over_week_delta_pct"] = "not_available"

        with self.assertRaises(ContractValidationError) as ctx:
            validate_metrics_json(metrics)

        self.assertIn("week_over_week_delta_pct", str(ctx.exception))

    def test_validate_metrics_json_rejects_top_product_wrong_shape(self) -> None:
        metrics = _valid_metrics()
        metrics["top_products"][0] = {"product_name": "Milk", "revenue": 700.0}

        with self.assertRaises(ContractValidationError) as ctx:
            validate_metrics_json(metrics)

        self.assertIn("metrics.top_products[0]", str(ctx.exception))

    def test_build_llm_narration_input_includes_guardrails_and_format(self) -> None:
        metrics = _valid_metrics()

        payload = build_llm_narration_input(
            metrics_json=metrics,
            retrieved_summaries=[{"week": "2026-02-16/2026-02-22", "summary": "Stable sales"}],
            business_profile={"business_type": "retail", "currency": "KES", "reporting_day": "Sunday"},
        )

        self.assertIn("output_format", payload)
        self.assertIn("guardrails", payload)
        self.assertTrue(payload["guardrails"]["llm_must_not_invent_numbers"])
        self.assertEqual(payload["guardrails"]["on_missing_data_use"], UNAVAILABLE)

    def test_build_llm_narration_input_rejects_bad_retrieved_summaries_type(self) -> None:
        metrics = _valid_metrics()

        with self.assertRaises(ContractValidationError) as ctx:
            build_llm_narration_input(
                metrics_json=metrics,
                retrieved_summaries={"week": "x"},  # type: ignore[arg-type]
                business_profile={"business_type": "retail", "currency": "KES", "reporting_day": "Sunday"},
            )

        self.assertIn("retrieved_summaries", str(ctx.exception))

    def test_validate_llm_output_accepts_valid_shape(self) -> None:
        output = {
            "summary": "Revenue grew week-over-week.",
            "insights": ["Top products contributed most of the revenue."],
            "recommendations": ["Prioritize stock for top contributors."],
        }
        validate_llm_output(output)

    def test_validate_llm_output_rejects_invalid_shape(self) -> None:
        with self.assertRaises(ContractValidationError):
            validate_llm_output({"summary": "", "insights": "bad", "recommendations": []})  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
