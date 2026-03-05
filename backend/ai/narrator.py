from __future__ import annotations

import json
from typing import Any
from urllib import error as url_error
from urllib import request as url_request

from backend.admin_settings_store import SETTINGS_STORE
from backend.metrics import build_llm_narration_input, validate_llm_output, validate_metrics_json


def _metrics_only_narration(metrics_json: dict[str, Any]) -> dict[str, Any]:
    week = metrics_json.get("week", {})
    revenue = metrics_json.get("weekly_revenue")
    delta = metrics_json.get("week_over_week_delta_pct")
    repeat_customers = metrics_json.get("repeat_customers")
    top_products = metrics_json.get("top_products") or []
    slow_movers = metrics_json.get("slow_movers") or []

    top_product_names = [str(item.get("product_name")) for item in top_products[:3] if item.get("product_name")]
    slow_product_names = [str(item.get("product_name")) for item in slow_movers[:3] if item.get("product_name")]

    summary = (
        f"Week {week.get('start', 'n/a')} to {week.get('end', 'n/a')}: "
        f"revenue {revenue}, WoW delta {delta}, repeat customers {repeat_customers}."
    )

    insights = []
    if top_product_names:
        insights.append(f"Top products by revenue share: {', '.join(top_product_names)}.")
    if slow_product_names:
        insights.append(f"Slow movers flagged: {', '.join(slow_product_names)}.")
    if not insights:
        insights.append("No notable top-product or slow-mover patterns were detected.")

    recommendations = [
        "Keep stock availability high for top contributors.",
        "Review promotion or bundling for slow-moving products.",
        "Track week-over-week movement before pricing changes.",
    ]

    return {
        "summary": summary,
        "insights": insights,
        "recommendations": recommendations,
        "source": "metrics_only_fallback",
    }


def _chat_completion_request(
    *,
    url: str,
    headers: dict[str, str],
    model: str,
    temperature: float,
    max_tokens: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    prompt = (
        "You are DataSoko narrator. Return strict JSON only with keys: summary, insights, recommendations. "
        "Never invent numbers. Use only metrics_json values provided."
    )

    body = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
        ],
    }

    req = url_request.Request(
        url=url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with url_request.urlopen(req, timeout=15) as response:  # noqa: S310
        raw = response.read().decode("utf-8")
    parsed = json.loads(raw)
    content = parsed.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    candidate = json.loads(content)
    if not isinstance(candidate, dict):
        raise ValueError("Narrator output must be a JSON object")
    return candidate


def _call_openai(payload: dict[str, Any], ai_settings: dict[str, Any], api_key: str) -> dict[str, Any]:
    return _chat_completion_request(
        url="https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        model=str(ai_settings.get("model") or "gpt-4.1-mini"),
        temperature=float(ai_settings.get("temperature") or 0.2),
        max_tokens=int(ai_settings.get("max_output_tokens") or 700),
        payload=payload,
    )


def _call_azure_openai(payload: dict[str, Any], ai_settings: dict[str, Any], api_key: str) -> dict[str, Any]:
    endpoint = (ai_settings.get("azure_endpoint") or "").rstrip("/")
    deployment = ai_settings.get("azure_deployment") or ai_settings.get("model")
    if not endpoint or not deployment:
        raise ValueError("Azure OpenAI endpoint/deployment missing")
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-08-01-preview"
    return _chat_completion_request(
        url=url,
        headers={"api-key": api_key, "Content-Type": "application/json"},
        model=str(deployment),
        temperature=float(ai_settings.get("temperature") or 0.2),
        max_tokens=int(ai_settings.get("max_output_tokens") or 700),
        payload=payload,
    )


def _resolve_ai_settings() -> dict[str, Any]:
    configured = SETTINGS_STORE.get_non_secret_settings().get("ai", {})
    return {
        "provider": str(configured.get("provider") or "azure_openai"),
        "model": str(configured.get("model") or "gpt-4.1-mini"),
        "temperature": float(configured.get("temperature") or 0.2),
        "max_output_tokens": int(configured.get("max_output_tokens") or 700),
        "strict_json_only": bool(configured.get("strict_json_only", True)),
        "metrics_only_fallback": bool(configured.get("metrics_only_fallback", True)),
        "azure_endpoint": configured.get("azure_endpoint") or None,
        "azure_deployment": configured.get("azure_deployment") or None,
    }


def generate_llm_narration(
    *,
    metrics_json: dict[str, Any],
    business_profile: dict[str, Any],
    retrieved_summaries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    validate_metrics_json(metrics_json)
    ai_settings = _resolve_ai_settings()
    input_payload = build_llm_narration_input(
        metrics_json=metrics_json,
        retrieved_summaries=retrieved_summaries or [],
        business_profile=business_profile,
    )

    api_key = SETTINGS_STORE.get_secret("ai_api_key")
    if not api_key:
        return _metrics_only_narration(metrics_json)

    try:
        provider = ai_settings["provider"]
        if provider == "openai":
            output = _call_openai(input_payload, ai_settings, api_key)
        else:
            output = _call_azure_openai(input_payload, ai_settings, api_key)
        validate_llm_output(output)
        output["source"] = provider
        return output
    except (ValueError, json.JSONDecodeError, url_error.URLError, url_error.HTTPError):
        if ai_settings.get("metrics_only_fallback", True):
            return _metrics_only_narration(metrics_json)
        raise
