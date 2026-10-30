# Project Instructions

- Keep decision thresholds and financial assumptions in `config.yaml`; do not hard-code policy values in the UI.
- Keep `final_status` out of pre-dispatch decisions and any feature calculation used for routing.
- The default experience must work without API credentials or network calls. LLM review stays opt-in and may only add a high-confidence text-quality flag.
- Treat customer names, phone numbers, and addresses as personal data. Do not add them to logs, screenshots, public docs, or external requests without explicit approval.
- Keep explanations actionable for operations and distinguish measured results from modeled assumptions.
- Add or update focused unit tests for decision and WhatsApp state changes.