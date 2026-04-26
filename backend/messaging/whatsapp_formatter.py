from __future__ import annotations

from typing import Any

UNAVAILABLE = "unavailable"
RECOMMENDATIONS = {
    "retail": "Recommendation: Restock top seller and run a promo on slow movers this week.",
    "pharmacy": "Recommendation: Replenish fast-moving OTC items and review expiry risk on slow movers.",
    "hardware": "Recommendation: Reorder top SKUs early and bundle slow-moving stock with best sellers.",
}


def _fmt_money(value: Any, currency: str = "KES") -> str:
    if isinstance(value, (int, float)):
        return f"{currency} {value:,.2f}"
    return UNAVAILABLE


def _fmt_pct_with_arrow(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "↔ unavailable"
    arrow = "↗" if value > 0 else ("↘" if value < 0 else "↔")
    sign = "+" if value > 0 else ""
    return f"{arrow} {sign}{value:.2f}%"


def format_weekly_whatsapp_message(
    *,
    metrics: dict[str, Any],
    business_name: str = "Your Business",
    currency: str = "KES",
    sme_type: str = "retail",
) -> str:
    week = metrics.get("week", {})
    week_start = week.get("start", UNAVAILABLE)
    week_end = week.get("end", UNAVAILABLE)

    revenue_text = _fmt_money(metrics.get("weekly_revenue"), currency=currency)
    wow_text = _fmt_pct_with_arrow(metrics.get("week_over_week_delta_pct"))
    atv_text = _fmt_money(metrics.get("avg_transaction_value"), currency=currency)

    top_products = metrics.get("top_products") or []
    if top_products:
        top_lines = []
        for item in top_products[:3]:
            name = item.get("product_name", "unknown")
            contrib = item.get("contribution_pct", UNAVAILABLE)
            if isinstance(contrib, (int, float)):
                top_lines.append(f"- {name}: {contrib:.2f}%")
            else:
                top_lines.append(f"- {name}: unavailable")
        top_products_text = "\n".join(top_lines)
    else:
        top_products_text = "- unavailable"

    slow_movers = metrics.get("slow_movers") or []
    if slow_movers:
        slow_lines = [f"- {item.get('product_name', 'unknown')}" for item in slow_movers[:3]]
        slow_text = "\n".join(slow_lines)
    else:
        slow_text = "- none in selected window"

    recommendation = RECOMMENDATIONS.get(sme_type.lower(), RECOMMENDATIONS["retail"])

    message = (
        f"📊 Weekly Update ({week_start} to {week_end})\n"
        f"Business: {business_name}\n\n"
        f"Revenue: {revenue_text}\n"
        f"WoW Change: {wow_text}\n"
        f"Avg Transaction: {atv_text}\n"
        f"Repeat Customers: {metrics.get('repeat_customers', UNAVAILABLE)}\n\n"
        f"Top Products\n"
        f"{top_products_text}\n\n"
        f"Slow Movers\n"
        f"{slow_text}\n\n"
        f"{recommendation}"
    )
    return message
