import json
from collections import Counter, defaultdict

from src.data_profile import DATA_PATH, load_orders, normalized
from src.decision_engine import ACTION_LABELS, assess_order, estimate_impact, load_config


def summarize_month(month: str, orders: list[dict[str, str]], config: dict) -> dict[str, object]:
    selected = [order for order in orders if order.get("order_datetime", "").startswith(month)]
    actions: dict[str, list[dict]] = defaultdict(list)
    total_impact = Counter()
    for order in selected:
        decision = assess_order(order, config)
        impact = estimate_impact(decision, config)
        actions[decision["action"]].append(order)
        total_impact.update(impact)

    buckets = {}
    for action, label in ACTION_LABELS.items():
        records = actions[action]
        rto_count = sum(normalized(order.get("final_status")) == "rto" for order in records)
        buckets[action] = {
            "label": label,
            "orders": len(records),
            "observed_rto": rto_count,
            "observed_rto_rate": round(rto_count / len(records), 4) if records else None,
        }
    return {
        "month": month,
        "orders": len(selected),
        "buckets": buckets,
        "estimated_avoided_rto_inr": round(total_impact["avoided_rto_inr"], 2),
        "estimated_lost_contribution_inr": round(total_impact["lost_contribution_inr"], 2),
        "estimated_discount_cost_inr": round(total_impact["discount_cost_inr"], 2),
        "estimated_net_impact_inr": round(total_impact["net_impact_inr"], 2),
    }


if __name__ == "__main__":
    orders = load_orders(DATA_PATH)
    config = load_config()
    months = sorted({order.get("order_datetime", "")[:7] for order in orders if order.get("order_datetime")})
    month = months[-1]
    print(json.dumps(summarize_month(month, orders, config), indent=2))