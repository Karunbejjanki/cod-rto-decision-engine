import os
import sys
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_profile import DATA_PATH, load_orders, profile
from src.decision_engine import ACTION_LABELS, assess_order, estimate_impact, load_config
from src.llm_review import review_order
from src.whatsapp_flow import opening_message, simulate_reply


st.set_page_config(page_title="COD Control Desk", page_icon="📦", layout="wide")
st.markdown(
    """
    <style>
    :root { --ink: #1d2925; --muted: #64736c; --green: #176b52; --mint: #e8f3ed; --line: #dce5df; }
    .stApp { background: #f7f8f5; color: var(--ink); }
    h1, h2, h3 { font-family: Georgia, 'Times New Roman', serif; color: var(--ink); }
    [data-testid="stMetric"] { background: #fff; border: 1px solid var(--line); padding: 14px 16px; border-radius: 6px; }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stMetricValue"] { color: var(--green); }
    div.stButton > button[kind="primary"] { background: var(--green); border-color: var(--green); }
    [data-testid="stSidebar"] { background: #eef3ef; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_default_data() -> list[dict[str, str]]:
    return load_orders(DATA_PATH)


def load_uploaded_data(upload: object) -> list[dict[str, str]]:
    raw = upload.getvalue().decode("utf-8-sig")
    return pd.read_csv(StringIO(raw), dtype=str, keep_default_na=False).to_dict(orient="records")


def money(value: float) -> str:
    return f"₹{value:,.0f}"


def decision_frame(rows: list[dict[str, str]], config: dict) -> pd.DataFrame:
    decisions = []
    for row in rows:
        decision = assess_order(row, config)
        impact = estimate_impact(decision, config)
        decisions.append({**row, **decision, **impact})
    frame = pd.DataFrame(decisions)
    frame["_date"] = pd.to_datetime(frame["order_datetime"], errors="coerce").dt.date
    return frame


def show_dashboard(frame: pd.DataFrame, raw_profile: dict, config: dict) -> None:
    latest = frame["_date"].max()
    if pd.isna(latest):
        st.error("No valid order dates were found in this CSV.")
        return
    latest_date = latest if isinstance(latest, date) else latest.date()
    yesterday = date.today() - timedelta(days=1)
    default_day = yesterday if yesterday in set(frame["_date"]) else latest_date
    selected_day = st.date_input("Order date", value=default_day, min_value=min(frame["_date"]), max_value=max(frame["_date"]))
    day = frame[frame["_date"] == selected_day]
    if day.empty:
        st.info(f"No sample orders exist for {selected_day:%d %b %Y}. The supplied file runs through {latest_date:%d %b %Y}; select a date with sample orders to replay the policy.")
        return
    if latest_date < yesterday:
        st.warning(f"Demo data ends {latest_date:%d %b %Y}; this is a replay of the latest available day, not live yesterday's production orders.")

    counts = day["action"].value_counts().reindex(ACTION_LABELS, fill_value=0)
    avoided = float(day["avoided_rto_inr"].sum())
    lost = float(day["lost_contribution_inr"].sum())
    discount = float(day["discount_cost_inr"].sum())
    net = float(day["net_impact_inr"].sum())
    cols = st.columns(4)
    for column, action in zip(cols, ACTION_LABELS):
        column.metric(ACTION_LABELS[action], int(counts[action]))
    st.caption(f"Policy replay for {selected_day:%A, %d %B %Y}. Outcome labels are not used in routing.")

    cols = st.columns(4)
    cols[0].metric("Expected RTO cost avoided", money(avoided))
    cols[1].metric("Expected genuine-order contribution lost", money(lost))
    cols[2].metric("Expected prepaid discounts", money(discount))
    cols[3].metric("Estimated net impact", money(net), delta="vs. no intervention")

    chart, table = st.columns([1.15, 1])
    with chart:
        st.subheader("Action mix")
        st.bar_chart(pd.DataFrame({"Orders": counts.rename(index=ACTION_LABELS)}), color="#176b52")
    with table:
        st.subheader("Expected economics")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Measure": "RTO losses avoided", "Estimate": money(avoided)},
                    {"Measure": "Genuine contribution lost", "Estimate": money(lost)},
                    {"Measure": "Prepaid discount spend", "Estimate": money(discount)},
                    {"Measure": "Net impact", "Estimate": money(net)},
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    st.caption(
        "Impact is modeled, not observed: uses current risk score, 65% confirmation response, 60% reduction in RTO risk after confirmation, "
        "35% prepaid uptake, 28% COD vs 4% prepaid RTO, and configured discount. See config.yaml."
    )
    st.subheader("Orders in this replay")
    visible = day[["order_id", "action_label", "risk", "order_value", "final_status"]].copy()
    visible["risk"] = visible["risk"].map(lambda value: f"{value:.0%}")
    visible["order_value"] = visible["order_value"].map(lambda value: money(float(value)))
    st.dataframe(visible, hide_index=True, use_container_width=True)
    st.caption(
        f"Data checks: {raw_profile['duplicate_id_groups']} duplicated order-ID groups, "
        f"{raw_profile['missing_pincode_count']} missing pincodes, {raw_profile['invalid_phone_length_count']} non-10-digit phone values."
    )


def show_order_review(config: dict) -> None:
    st.subheader("Review a new COD order")
    with st.form("order_review"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Customer name", placeholder="Asha Mehta")
            phone = st.text_input("Phone", placeholder="9876543210")
            city = st.text_input("City", placeholder="Pune")
        with col2:
            address = st.text_input("Delivery address", placeholder="12 MG Road, near Hanuman Mandir")
            pincode = st.text_input("Pincode", placeholder="411001")
            value = st.number_input("Order value (₹)", min_value=0, value=649, step=1)
        prior_orders = st.number_input("Prior orders", min_value=0, value=0, step=1)
        prior_rto = st.number_input("Prior RTOs", min_value=0, value=0, step=1)
        enable_ai = st.checkbox("Use optional AI text review for Hinglish/address meaning", value=False)
        submitted = st.form_submit_button("Evaluate order", type="primary")

    if submitted:
        order = {
            "customer_name": name,
            "phone": phone,
            "address": address,
            "city": city,
            "pincode": pincode,
            "order_value": value,
            "customer_prior_orders": prior_orders,
            "customer_prior_rto": prior_rto,
        }
        llm_result = None
        if enable_ai:
            st.warning("The optional provider receives the name, address, city, and pincode only. Do not enable without approved data-processing terms. Phone and order ID are never sent.")
            try:
                llm_result = review_order(order, config["policy"].get("llm", {}).get("model", "gpt-4o-mini"))
            except Exception as error:
                st.error(f"AI review unavailable; deterministic checks remain active ({type(error).__name__}).")
        decision = assess_order(order, config, llm_result)
        st.success(f"{decision['action_label']} · estimated RTO risk {decision['risk']:.0%}")
        for reason in decision["reasons"]:
            st.write(f"- {reason}")
        st.json(decision["signals"])


def show_whatsapp_mock(config: dict) -> None:
    st.subheader("WhatsApp flow simulator")
    st.caption("In production, send within 5 minutes of order placement and before warehouse handoff. Use the customer's saved language preference; Hinglish is the mock default.")
    col1, col2 = st.columns(2)
    with col1:
        flow = st.radio("Flow", ["confirm", "nudge_prepaid"], format_func=lambda key: ACTION_LABELS[key])
        language = st.selectbox("Message language", ["Hinglish", "English"])
        order_id = st.text_input("Mock order ID", "KT-DEMO-001")
    with col2:
        economics = config["policy"]["economics"]
        st.info(opening_message(flow, language, order_id, int(economics["prepaid_discount_inr"])))
    reply_choice = st.radio("Customer response", ["YES", "NO", "Something random", "No reply for 24 hours"])
    paid = st.checkbox("Mark mock prepaid link as paid", disabled=flow != "nudge_prepaid")
    reply_map = {"Something random": "What is this?", "No reply for 24 hours": ""}
    reply = reply_map.get(reply_choice, reply_choice)
    elapsed = 24 if reply_choice == "No reply for 24 hours" else 0
    if flow == "nudge_prepaid" and reply == "YES" and not paid:
        st.caption("YES issues a mock payment link. This simulator does not represent a payment as complete until the box is selected.")
    if st.button("Simulate reply", type="primary"):
        result = simulate_reply(flow, reply, elapsed, paid, language)
        st.success(f"State: {result['status'].replace('_', ' ').title()}")
        st.write(result["message"])
    st.caption("Mock only: no WhatsApp messages or payment links are sent. In production, store consent, timestamps, delivery receipts, and idempotent order-state transitions.")


def show_policy(config: dict) -> None:
    policy = config["policy"]
    st.subheader("Current editable policy")
    threshold_table = pd.DataFrame(
        [{"Action": ACTION_LABELS[key], "Risk from": f"{value:.0%}"} for key, value in policy["thresholds"].items()]
    )
    st.dataframe(threshold_table, hide_index=True, use_container_width=True)
    st.caption("Change the values in config.yaml; restart/reload the app. No source-code change is needed.")
    e = policy["economics"]
    f = policy.get("flow", {})
    rto_cost = (
        float(e["forward_shipping_inr"])
        + float(e["return_shipping_inr"])
        + float(e["packaging_handling_inr"])
        + float(e["damaged_return_rate"]) * float(e["product_cost_inr"])
    )
    cols = st.columns(3)
    cols[0].metric("Cost per RTO", money(rto_cost))
    cols[1].metric("COD to prepaid RTO gap", f"{float(e['cod_rto_rate']) - float(e['prepaid_rto_rate']):.0%}")
    cols[2].metric("Prepaid discount", money(float(e["prepaid_discount_inr"])))
    gross = 649 * float(e["gross_margin_rate"])
    cancel_threshold = gross / (gross + rto_cost)
    st.write(
        f"At ₹649 AOV and {float(e['gross_margin_rate']):.0%} gross margin, a stand-alone cancel beats shipping only above "
        f"{cancel_threshold:.1%} estimated RTO probability (expected avoided RTO cost vs expected delivered contribution). "
        "That is why first-time status alone does not trigger cancellation."
    )
    flow_table = pd.DataFrame(
        [
            {"Assumption": "Confirmation response", "Value": f"{float(f.get('confirmation_response_rate', 0.65)):.0%}"},
            {"Assumption": "RTO-risk reduction after confirmation", "Value": f"{float(f.get('confirmation_rto_reduction', 0.60)):.0%}"},
            {"Assumption": "Prepaid nudge uptake", "Value": f"{float(f.get('prepaid_nudge_take_rate', 0.35)):.0%}"},
            {"Assumption": "No-response timeout", "Value": f"{int(f.get('timeout_hours', 24))} hours"},
        ]
    )
    st.dataframe(flow_table, hide_index=True, use_container_width=True)


def main() -> None:
    st.title("COD control desk")
    st.caption("Decision support for Cash on Delivery orders · deterministic by default · human-readable reasons")
    config = load_config()
    with st.sidebar:
        st.header("Data source")
        upload = st.file_uploader("Upload orders CSV", type=["csv"])
        st.caption("Default: data/orders_sample.csv")
    try:
        orders = load_uploaded_data(upload) if upload else load_default_data()
        data_profile = profile(orders)
        frame = decision_frame(orders, config)
    except Exception as error:
        st.error(f"Could not load this CSV: {error}")
        st.stop()

    st.caption(f"{len(orders):,} orders · data through {data_profile['date_range'][1][:10]} · {data_profile['cod_rto_rate']:.1%} raw RTO rate")
    tabs = st.tabs(["Dashboard", "New order", "WhatsApp", "Policy"])
    with tabs[0]:
        show_dashboard(frame, data_profile, config)
    with tabs[1]:
        show_order_review(config)
    with tabs[2]:
        show_whatsapp_mock(config)
    with tabs[3]:
        show_policy(config)


if __name__ == "__main__":
    main()