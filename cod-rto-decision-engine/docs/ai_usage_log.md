# AI Usage Log

- GitHub Copilot was used to scaffold the Python/Streamlit prototype, draft the rules engine, tests, and business documents. The provided sample was analyzed locally with Python and PowerShell; no external AI service received the order file.
- The optional OpenAI-backed text reviewer is included for interpreting Hinglish addresses and obvious placeholder names. It is disabled by default, was not called while creating this submission, and requires an explicit UI opt-in plus `ENABLE_LLM_REVIEW=1` and an API key. The prompt does not send phone numbers or order IDs. Name/address data is still personal data, so production use requires privacy and vendor approval.

## Weak outputs caught and corrected

- **Wrong file-location assumption:** initial tooling tried to copy the CSV from Downloads into a project folder. The active workspace already contained the file at `D:\workspace\orders_sample.csv`; the project was moved under `D:\workspace` and the copy was made from there.
- **Overconfident risk interpretation:** a first draft treated additive rule scores as if they were calibrated probabilities. The prototype now labels them as a rules-based pilot estimate, exposes all inputs in `config.yaml`, and marks dashboard money as scenario estimates. A future model needs time-based validation and calibration before automatic cancellation.
- **Import/test setup issue:** the first unit-test run could not import the package and then revealed that PyYAML was not installed. Package markers and relative imports were added, and the dependency was declared in `requirements.txt` before retrying validation.