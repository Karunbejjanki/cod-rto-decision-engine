import json
import os
from typing import Any


def review_order(order: dict[str, Any], model: str = "gpt-4o-mini") -> dict[str, Any] | None:
    """Optionally interpret Hinglish address/name text; no contact or order IDs are sent."""
    if os.getenv("ENABLE_LLM_REVIEW") != "1" or not os.getenv("OPENAI_API_KEY"):
        return None

    from openai import OpenAI

    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Assess whether the supplied customer name looks like an obvious test/placeholder and "
                    "whether the address contains enough actionable delivery information. Understand "
                    "English and Hinglish. Do not infer risk from language, region, religion, caste, or "
                    "other protected traits. Return JSON with name_suspect, address_incomplete, "
                    "confidence (0 to 1), reason (under 20 words). Do not decide whether to cancel."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "customer_name": str(order.get("customer_name", ""))[:100],
                        "address": str(order.get("address", ""))[:300],
                        "city": str(order.get("city", ""))[:80],
                        "pincode": str(order.get("pincode", ""))[:10],
                    },
                    ensure_ascii=True,
                ),
            },
        ],
    )
    try:
        result = json.loads(response.choices[0].message.content or "{}")
        return {
            "name_suspect": bool(result.get("name_suspect")),
            "address_incomplete": bool(result.get("address_incomplete")),
            "confidence": float(result.get("confidence", 0)),
            "reason": str(result.get("reason", ""))[:160],
        }
    except (ValueError, TypeError, IndexError, AttributeError):
        return None