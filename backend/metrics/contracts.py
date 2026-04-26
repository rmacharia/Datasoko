from __future__ import annotations

from typing import Any


UNAVAILABLE = "unavailable"

METRICS_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "week",
        "weekly_revenue",
        "previous_week_revenue",
        "week_over_week_delta_pct",
        "top_products",
        "slow_movers",
        "repeat_customers",
        "avg_transaction_value",
        "meta",
    ],
    "properties": {
        "week": {
            "type": "object",
            "required": ["start", "end", "previous_start", "previous_end"],
            "properties": {
                "start": {"type": "string"},
                "end": {"type": "string"},
                "previous_start": {"type": "string"},
                "previous_end": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "weekly_revenue": {"type": "number"},
        "previous_week_revenue": {"type": "number"},
        "week_over_week_delta_pct": {
            "oneOf": [
                {"type": "number"},
                {"type": "string", "enum": [UNAVAILABLE]},
            ]
        },
        "top_products": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["product_name", "revenue", "contribution_pct"],
                "properties": {
                    "product_name": {"type": "string"},
                    "revenue": {"type": "number"},
                    "contribution_pct": {"type": "number"},
                },
                "additionalProperties": False,
            },
        },
        "slow_movers": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["product_name", "last_sale_date", "days_since_last_sale"],
                "properties": {
                    "product_name": {"type": "string"},
                    "last_sale_date": {"type": "string"},
                    "days_since_last_sale": {"type": "integer"},
                },
                "additionalProperties": False,
            },
        },
        "repeat_customers": {"type": "integer"},
        "avg_transaction_value": {
            "oneOf": [
                {"type": "number"},
                {"type": "string", "enum": [UNAVAILABLE]},
            ]
        },
        "meta": {
            "type": "object",
            "required": ["slow_mover_days", "top_n_products", "records_processed"],
            "properties": {
                "slow_mover_days": {"type": "integer"},
                "top_n_products": {"type": "integer"},
                "records_processed": {"type": "integer"},
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}


LLM_OUTPUT_FORMAT: dict[str, Any] = {
    "type": "object",
    "required": ["summary", "insights", "recommendations"],
    "properties": {
        "summary": {"type": "string"},
        "insights": {"type": "array", "items": {"type": "string"}},
        "recommendations": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}


class ContractValidationError(ValueError):
    pass


def _require_keys(obj: dict[str, Any], keys: list[str], *, context: str) -> None:
    missing = [k for k in keys if k not in obj]
    if missing:
        raise ContractValidationError(f"{context}: missing keys {missing}")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_number_or_unavailable(value: Any) -> bool:
    return _is_number(value) or value == UNAVAILABLE


def validate_metrics_json(metrics: dict[str, Any]) -> None:
    _require_keys(
        metrics,
        [
            "week",
            "weekly_revenue",
            "previous_week_revenue",
            "week_over_week_delta_pct",
            "top_products",
            "slow_movers",
            "repeat_customers",
            "avg_transaction_value",
            "meta",
        ],
        context="metrics",
    )

    if not isinstance(metrics["week"], dict):
        raise ContractValidationError("metrics.week must be an object")

    _require_keys(metrics["week"], ["start", "end", "previous_start", "previous_end"], context="metrics.week")

    if not _is_number(metrics["weekly_revenue"]):
        raise ContractValidationError("metrics.weekly_revenue must be numeric")

    if not _is_number(metrics["previous_week_revenue"]):
        raise ContractValidationError("metrics.previous_week_revenue must be numeric")

    if not _is_number_or_unavailable(metrics["week_over_week_delta_pct"]):
        raise ContractValidationError("metrics.week_over_week_delta_pct must be numeric or 'unavailable'")

    if not isinstance(metrics["top_products"], list):
        raise ContractValidationError("metrics.top_products must be a list")

    for idx, item in enumerate(metrics["top_products"]):
        if not isinstance(item, dict):
            raise ContractValidationError(f"metrics.top_products[{idx}] must be an object")
        _require_keys(item, ["product_name", "revenue", "contribution_pct"], context=f"metrics.top_products[{idx}]")
        if not isinstance(item["product_name"], str):
            raise ContractValidationError(f"metrics.top_products[{idx}].product_name must be a string")
        if not _is_number(item["revenue"]):
            raise ContractValidationError(f"metrics.top_products[{idx}].revenue must be numeric")
        if not _is_number(item["contribution_pct"]):
            raise ContractValidationError(f"metrics.top_products[{idx}].contribution_pct must be numeric")

    if not isinstance(metrics["slow_movers"], list):
        raise ContractValidationError("metrics.slow_movers must be a list")

    for idx, item in enumerate(metrics["slow_movers"]):
        if not isinstance(item, dict):
            raise ContractValidationError(f"metrics.slow_movers[{idx}] must be an object")
        _require_keys(
            item,
            ["product_name", "last_sale_date", "days_since_last_sale"],
            context=f"metrics.slow_movers[{idx}]",
        )
        if not isinstance(item["product_name"], str):
            raise ContractValidationError(f"metrics.slow_movers[{idx}].product_name must be a string")
        if not isinstance(item["last_sale_date"], str):
            raise ContractValidationError(f"metrics.slow_movers[{idx}].last_sale_date must be a string")
        if not isinstance(item["days_since_last_sale"], int):
            raise ContractValidationError(f"metrics.slow_movers[{idx}].days_since_last_sale must be an integer")

    if not isinstance(metrics["repeat_customers"], int):
        raise ContractValidationError("metrics.repeat_customers must be an integer")

    if not _is_number_or_unavailable(metrics["avg_transaction_value"]):
        raise ContractValidationError("metrics.avg_transaction_value must be numeric or 'unavailable'")

    if not isinstance(metrics["meta"], dict):
        raise ContractValidationError("metrics.meta must be an object")
    _require_keys(metrics["meta"], ["slow_mover_days", "top_n_products", "records_processed"], context="metrics.meta")


def build_llm_narration_input(
    *,
    metrics_json: dict[str, Any],
    retrieved_summaries: list[dict[str, Any]],
    business_profile: dict[str, Any],
) -> dict[str, Any]:
    """
    Build strict LLM narration input payload.

    LLM role is narration only; this payload must contain deterministic metric outputs.
    """
    validate_metrics_json(metrics_json)

    if not isinstance(retrieved_summaries, list):
        raise ContractValidationError("retrieved_summaries must be a list")

    if not isinstance(business_profile, dict):
        raise ContractValidationError("business_profile must be an object")

    return {
        "metrics_json": metrics_json,
        "retrieved_summaries": retrieved_summaries,
        "business_profile": business_profile,
        "output_format": {
            "summary": "string",
            "insights": ["string"],
            "recommendations": ["string"],
        },
        "guardrails": {
            "llm_must_not_invent_numbers": True,
            "on_missing_data_use": UNAVAILABLE,
            "json_only_output": True,
        },
    }


def validate_llm_output(output: dict[str, Any]) -> None:
    _require_keys(output, ["summary", "insights", "recommendations"], context="llm_output")
    if not isinstance(output["summary"], str) or not output["summary"].strip():
        raise ContractValidationError("llm_output.summary must be a non-empty string")
    if not isinstance(output["insights"], list) or not all(isinstance(item, str) for item in output["insights"]):
        raise ContractValidationError("llm_output.insights must be a string array")
    if not isinstance(output["recommendations"], list) or not all(
        isinstance(item, str) for item in output["recommendations"]
    ):
        raise ContractValidationError("llm_output.recommendations must be a string array")
