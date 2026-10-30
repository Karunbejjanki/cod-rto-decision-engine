import csv
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "orders_sample.csv"
PLACEHOLDER_ADDRESSES = {"", ".", "xyz", "call me", "home", "near station"}
SUSPECT_NAME_PATTERN = re.compile(r"\b(test|qwerty|asdf|abc|xyz|na)\b", re.IGNORECASE)


def load_orders(path: Path = DATA_PATH) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def normalized(value: str | None) -> str:
    return (value or "").strip().lower()


def is_suspect_name(order: dict[str, str]) -> bool:
    return bool(SUSPECT_NAME_PATTERN.search(order.get("customer_name", "")))


def has_weak_address(order: dict[str, str]) -> bool:
    address = normalized(order.get("address"))
    city = normalized(order.get("city"))
    return address in PLACEHOLDER_ADDRESSES or (bool(city) and address == city)


def profile(orders: list[dict[str, str]]) -> dict[str, object]:
    status_counts = Counter(normalized(order.get("final_status")) for order in orders)
    id_counts = Counter(order.get("order_id", "").strip() for order in orders)
    cod_orders = [order for order in orders if normalized(order.get("payment_method")) == "cod"]
    suspicious_names = [order for order in orders if is_suspect_name(order)]
    weak_addresses = [order for order in orders if has_weak_address(order)]
    first_orders = [order for order in orders if int(order.get("customer_prior_orders") or 0) == 0]
    repeat_orders = [order for order in orders if int(order.get("customer_prior_orders") or 0) > 0]
    dates = [datetime.strptime(order["order_datetime"], "%Y-%m-%d %H:%M") for order in orders]

    def rto_rate(group: list[dict[str, str]]) -> float | None:
        if not group:
            return None
        return round(sum(normalized(order.get("final_status")) == "rto" for order in group) / len(group), 4)

    return {
        "rows": len(orders),
        "status_counts": dict(status_counts),
        "cod_orders": len(cod_orders),
        "cod_rto_rate": rto_rate(cod_orders),
        "duplicate_id_groups": sum(count > 1 for count in id_counts.values()),
        "duplicate_id_extra_rows": sum(count - 1 for count in id_counts.values() if count > 1),
        "suspect_name_count": len(suspicious_names),
        "suspect_name_rto_rate": rto_rate(suspicious_names),
        "weak_address_count": len(weak_addresses),
        "weak_address_rto_rate": rto_rate(weak_addresses),
        "first_order_count": len(first_orders),
        "first_order_rto_rate": rto_rate(first_orders),
        "repeat_order_count": len(repeat_orders),
        "repeat_order_rto_rate": rto_rate(repeat_orders),
        "missing_pincode_count": sum(not order.get("pincode", "").strip() for order in orders),
        "invalid_phone_length_count": sum(
            len(re.sub(r"\D", "", order.get("phone", ""))) != 10 for order in orders
        ),
        "zero_value_count": sum(float(order.get("order_value") or 0) <= 0 for order in orders),
        "date_range": [min(dates).isoformat(), max(dates).isoformat()],
    }


if __name__ == "__main__":
    import json

    print(json.dumps(profile(load_orders()), indent=2))