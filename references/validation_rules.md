# Input Validation Rules

Run these checks before metric computation. If a check fails, ask for clarification.

## Universal Checks

- Confirm business type: `saas`, `ecommerce`, `services`, `freelancer`, `professional_practice`, or `other`.
- Confirm analysis period: default to latest completed calendar month.
- Confirm currency is consistent across all sources.
- If a required field is missing for a metric, return `insufficient_data` and list `missing_inputs`.

## Bank CSV Checks

- Verify debit/credit direction is correct.
- Ensure balances are numeric and in chronological order.
- If only one month exists, do not produce trend conclusions.

## Stripe Export Checks

- Confirm export is from live mode, not test mode.
- Filter out failed/pending/refunded records for recognized revenue.
- Separate recurring subscription revenue from one-time payments.

## QBO/Xero Export Checks

- Ask whether report basis is cash or accrual.
- Use a monthly P&L export, not annual aggregate only.
- If combining with bank data, note basis differences in the report.

## Edge-Case Guardrails

- Revenue growth is insufficient when prior-period revenue is missing or <= 0.
- LTV is insufficient when churn is missing or <= 0.
- CAC is insufficient when new customers <= 0.
- NRR is insufficient when starting MRR is missing or <= 0.
- Runway is insufficient when net burn is missing or non-positive.
