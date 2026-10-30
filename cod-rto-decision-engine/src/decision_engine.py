import re
from pathlib import Path
from typing import Any

import yaml

from .data_profile import has_weak_address, is_suspect_name


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"
ACTION_LABELS = {
    "ship_as_is": "Ship as-is",
    "confirm": "Ship after confirmation",
    "nudge_prepaid": "Nudge to prepaid",
    "hold_cancel": "Hold / cancel",
}
DEFAULT_CONFIG: dict[str, Any] = {
    "policy": {
        "thresholds": {"nudge_prepaid": 0.38, "confirm": 0.52, "hold_cancel": 0.72},
        "risk_adjustments": {
            "suspect_name": 0.30,
            "weak_address": 0.18,
            "invalid_phone": 0.13,
            "invalid_pincode": 0.12,
            "prior_rto": 0.12,
            "repeat_without_prior_rto": -0.05,
        },
        "economics": {
            "forward_shipping_inr": 65,
            "return_shipping_inr": 65,
            "packaging_handling_inr": 25,
            "damaged_return_rate": 0.08,
            "product_cost_inr": 180,
            "gross_margin_rate": 0.62,
            "prepaid_discount_inr": 25,
            "cod_rto_rate": 0.28,
            "prepaid_rto_rate": 0.04,
        },
    }
}
NAME_SIGNAL = re.compile(r"\b(test|qwerty|asdf|abc|xyz|na)\b", re.IGNORECASE)


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        loaded = yaml.safe_load(source) or {}
    return deep_merge(DEFAULT_CONFIG, loaded)


def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def effective_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    return deep_merge(DEFAULT_CONFIG, config or {})


def _phone_is_valid(value: str) -> bool:
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    return len(digits) == 10


def assess_order(
    order: dict[str, Any],
    config: dict[str, Any] | None = None,
    llm_review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score only pre-dispatch fields; final_status is intentionally ignored."""
    policy = effective_config(config)["policy"]
    adjustments = policy["risk_adjustments"]
    signals = {
        "suspect_name": is_suspect_name({"customer_name": str(order.get("customer_name", ""))}),
        "weak_address": has_weak_address(
            {"address": str(order.get("address", "")), "city": str(order.get("city", ""))}
        ),
        "invalid_phone": not _phone_is_valid(str(order.get("phone", ""))),
        "invalid_pincode": not bool(re.fullmatch(r"\d{6}", str(order.get("pincode", "")).strip())),
    }
    llm_reason = ""
    if llm_review:
        confidence = float(llm_review.get("confidence", 0))
        if confidence >= 0.8:
            signals["suspect_name"] |= bool(llm_review.get("name_suspect"))
            signals["weak_address"] |= bool(llm_review.get("address_incomplete"))
            llm_reason = str(llm_review.get("reason", ""))

    try:
        prior_orders = max(0, int(order.get("customer_prior_orders") or 0))
        prior_rto = max(0, int(order.get("customer_prior_rto") or 0))
    except (TypeError, ValueError):
        prior_orders, prior_rto = 0, 0

    score = 0.284
    reasons = ["Starting point: 28.4% COD RTO rate in the supplied sample."]
    for key, active in signals.items():
        if active:
            score += float(adjustments[key])
            descriptions = {
                "suspect_name": "Name looks like a test or placeholder value.",
                "weak_address": "Address is missing a usable delivery location or landmark.",
                "invalid_phone": "Phone number is not a valid 10-digit number.",
                "invalid_pincode": "Pincode is missing or is not six digits.",
            }
            reasons.append(descriptions[key])
    if prior_rto > 0:
        score += float(adjustments["prior_rto"])
        reasons.append(f"Customer history includes {prior_rto} prior RTO(s).")
    elif prior_orders > 0:
        score += float(adjustments["repeat_without_prior_rto"])
        reasons.append("Repeat customer has no prior RTO recorded.")
    else:
        reasons.append("First order is not penalized; it is not evidence of delivery risk.")

    risk = min(0.95, max(0.02, score))
    thresholds = policy["thresholds"]
    if risk >= float(thresholds["hold_cancel"]):
        action = "hold_cancel"
    elif risk >= float(thresholds["confirm"]):
        action = "confirm"
    elif risk >= float(thresholds["nudge_prepaid"]):
        action = "nudge_prepaid"
    else:
        action = "ship_as_is"

    if llm_reason:
        reasons.append(f"Address/name review: {llm_reason}")
    reasons.append(f"Estimated RTO risk {risk:.0%}; policy routes this order to {ACTION_LABELS[action]}.")
    try:
        order_value = float(order.get("order_value") or 0)
    except (TypeError, ValueError):
        order_value = 0
    return {
        "order_id": str(order.get("order_id") or "new-order"),
        "action": action,
        "action_label": ACTION_LABELS[action],
        "risk": risk,
        "reasons": reasons,
        "signals": signals,
        "order_value": order_value,
        "first_order": prior_orders == 0,
    }


def estimate_rto_cost(config: dict[str, Any] | None = None) -> float:
    economics = effective_config(config)["policy"]["economics"]
    return (
        float(economics["forward_shipping_inr"])
        + float(economics["return_shipping_inr"])
        + float(economics["packaging_handling_inr"])
        + float(economics["damaged_return_rate"]) * float(economics["product_cost_inr"])
    )


def estimate_impact(decision: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, float]:
    """Expected avoided RTO cost, false-cancel contribution, discount and net."""
    settings = effective_config(config)
    policy = settings["policy"]
    economics = policy["economics"]
    flow = policy.get("flow", {})
    risk = float(decision["risk"])
    rto_cost = estimate_rto_cost(config)
    gross_margin = float(economics["gross_margin_rate"])
    order_value = float(decision.get("order_value", 0))
    avoided_rto = 0.0
    lost_contribution = 0.0
    discount_cost = 0.0
    action = decision["action"]

    if action == "hold_cancel":
        avoided_rto = risk * rto_cost
        lost_contribution = (1 - risk) * order_value * gross_margin
    elif action == "confirm":
        response_rate = float(flow.get("confirmation_response_rate", 0.65))
        effectiveness = float(flow.get("confirmation_rto_reduction", 0.60))
        avoided_rto = risk * (1 - response_rate * (1 - effectiveness)) * rto_cost
        lost_contribution = (1 - risk) * (1 - response_rate) * order_value * gross_margin
    elif action == "nudge_prepaid":
        uptake = float(flow.get("prepaid_nudge_take_rate", 0.35))
        rate_drop = max(0.0, float(economics["cod_rto_rate"]) - float(economics["prepaid_rto_rate"]))
        avoided_rto = uptake * rate_drop * rto_cost
        discount_cost = uptake * float(economics["prepaid_discount_inr"])

    return {
        "avoided_rto_inr": avoided_rto,
        "lost_contribution_inr": lost_contribution,
        "discount_cost_inr": discount_cost,
        "net_impact_inr": avoided_rto - lost_contribution - discount_cost,
    }