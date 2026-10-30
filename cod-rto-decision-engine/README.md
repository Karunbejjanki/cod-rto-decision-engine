# COD RTO Decision Engine

A small, local-first take-home prototype for routing COD orders, simulating WhatsApp responses, and estimating the financial trade-off between avoided RTOs and cancellations.

## Run in under 10 minutes

1. Install Python 3.11 or newer.
2. From this folder, create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies and start the app:

   ```powershell
   python -m pip install -r requirements.txt
   streamlit run app.py
   ```

4. Open the local URL printed by Streamlit. The default sample is `data/orders_sample.csv`; the dashboard can also accept another CSV with the same columns.

Run the tests with:

```powershell
python -m unittest discover -s tests -v
```

Regenerate the two-page memo PDF after editing its Markdown source:

```powershell
python -m src.render_memo
```

## What is included

- Four-way decision engine with plain-language reasons and settings in `config.yaml`.
- Founder dashboard with date replay, action counts, and scenario economics.
- New-order form and a deterministic WhatsApp/payment mock. Production timing is within five minutes of checkout and before warehouse handoff; use the customer's saved language preference (Hinglish is the mock default). No messages or payments are sent.
- Optional LLM name/address review, off by default. It is only called when `ENABLE_LLM_REVIEW=1`, `OPENAI_API_KEY` is set, and the operator checks the opt-in box. It receives the name, address, city, and pincode, never the phone or order ID. Confirm approved data-processing terms before enabling it.
- Founder memo, decision log, and AI usage log in `docs/`.

## Policy and economics

Edit `config.yaml` to change score thresholds, risk adjustments, costs, discounts, or WhatsApp response assumptions. The score is a transparent rules-based pilot estimate, not a statistically calibrated probability; displayed financial impact is therefore a scenario estimate and must be monitored against live outcomes before automated cancellation is enabled.

The sample contains order-level personal information. Keep the repository private unless the data is removed or permission to publish it is confirmed. Never commit API keys.

## Data caveats

The supplied sample has 2,018 rows from April 1 through September 30, 2026, 30 duplicate order-ID groups, and only COD orders. It does not contain October 29 production data, so the dashboard clearly labels its latest-day replay as a sample replay rather than live yesterday. `final_status` is used only for analysis/display and is excluded from routing.