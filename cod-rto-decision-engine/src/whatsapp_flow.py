from typing import Any


def opening_message(flow: str, language: str, order_id: str, discount: int = 25) -> str:
    if language == "English":
        if flow == "confirm":
            return f"Hi! Please confirm COD order {order_id}. Reply YES to ship or NO to cancel. We will hold it for 24 hours."
        return (
            f"Hi! Order {order_id}: pay online and save Rs {discount}. Reply YES for a secure payment link, "
            "or NO to keep COD. We will hold the order for 24 hours."
        )
    if flow == "confirm":
        return f"Namaste! Order {order_id} COD par hai. Bhejne ke liye YES, cancel karne ke liye NO reply karein. 24 ghante tak hold rahega."
    return (
        f"Namaste! Order {order_id} prepaid karne par Rs {discount} bachayein. Payment link ke liye YES, "
        "COD par rakhne ke liye NO reply karein. Order 24 ghante hold rahega."
    )


def simulate_reply(
    flow: str,
    reply: str,
    elapsed_hours: float = 0,
    paid: bool = False,
    language: str = "Hinglish",
) -> dict[str, str]:
    """Pure mock state transition; it never sends a real WhatsApp message."""
    if elapsed_hours >= 24 and (not reply.strip() or (flow == "nudge_prepaid" and reply.strip().upper() == "YES" and not paid)):
        return {"status": "hold_cancel", "message": "24 hours passed without confirmation/payment. Hold, then cancel; do not dispatch."}

    answer = reply.strip().upper()
    if flow == "confirm":
        if answer in {"YES", "Y", "HAAN", "JI"}:
            message = "Order confirmed. We will ship it COD." if language == "English" else "Order confirm ho gaya. COD par dispatch hoga."
            return {"status": "ship_as_is", "message": message}
        if answer in {"NO", "N", "NAHI"}:
            return {"status": "cancel", "message": "Customer declined. Cancel before dispatch."}
        return {"status": "clarify", "message": "Please reply only YES to ship or NO to cancel."}

    if answer in {"YES", "Y", "HAAN", "JI"}:
        if paid:
            return {"status": "ship_prepaid", "message": "Payment marked received in the mock. Release as prepaid."}
        return {"status": "awaiting_payment", "message": "Mock payment link issued. Release only after payment is marked received."}
    if answer in {"NO", "N", "NAHI"}:
        message = "Discount declined. Keep the order COD and ship as-is." if language == "English" else "Discount nahi chahiye. Order COD par bhej rahe hain."
        return {"status": "ship_as_is", "message": message}
    return {"status": "clarify", "message": "Reply YES for the prepaid link, or NO to keep COD."}