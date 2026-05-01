---
name: startup-financial-analyst
description: >
  Financial health analysis for startups and small businesses. Ingests bank
  CSV, accounting exports, and pasted figures. Computes shared business
  metrics first, then adds a short industry section (SaaS, e-commerce,
  services, freelancer/consulting) when enough data exists.
metadata:
  version: "1.0.0"
  author: "SlickBooks"
  tags: ["finance", "startup", "small-business", "cash-flow", "profitability"]
  license: "MIT"
  minAgentVersion: "1.0.0"
  openclaw:
    emoji: "📊"
    requires:
      anyBins: ["python3", "python", "uv"]
    os: ["linux", "darwin", "win32"]
---

# Startup Financial Analyst

Turn raw financial exports into a clear business-health snapshot.

## Scope

Designed for: SaaS, e-commerce, agencies/services, professional practices, freelancers, and consultants.

## Do Not Trigger If

- The user asks for audited accounting or tax filing advice.
- The user needs legal/compliance opinion instead of operational metrics.
- The user provides no financial numbers and refuses clarifications.

## Input Sources

- Bank statement CSV (recommended: latest completed month, preferably 3 months)
- Xero / QuickBooks P&L export CSV
- Stripe export CSV
- Pasted figures in chat

## Required User Prompting

Ask this first if not provided:

- Business type: `saas`, `ecommerce`, `services`, `freelancer`, `professional_practice`, or `other`
- Analysis period: default to latest completed calendar month
- Data coverage: ask for 3 months minimum for trends, 13 months preferred for YoY metrics

## Core Behavior

1. Compute common metrics for every business:
   - Revenue, Expenses, Net Profit/Loss, Profit Margin
   - Net Cash Flow, Cash Balance, Runway (if burning)
   - Revenue Growth (if prior period exists)
2. Compute the 12 advanced investor metrics only when required fields exist.
3. Never invent values. Missing inputs must return:
   - `label: insufficient_data`
   - `reason: Cannot be determined from the provided inputs.`
   - `missing_inputs: [...]`

## Minimum Inputs For All 12 Advanced Metrics

Ask for these fields when user wants the full 12-metric output:

- `current_cash`
- `monthly_revenue`
- `prev_monthly_revenue`
- `monthly_opex`
- `cogs`
- `sales_marketing_spend`
- `new_customers`
- `active_customers`
- `lost_customers`
- `starting_mrr`
- `churned_mrr`
- `expansion_mrr`
- `contraction_mrr`
- `arr_start`
- `arr_end`
- `revenue_growth_yoy_pct`
- `operating_margin_pct`

## Industry Add-On Metrics (2-3 only)

- `saas`: MRR/ARR, churn/NRR, CAC payback or LTV:CAC
- `ecommerce`: gross margin, AOV, ad-spend ratio or refund ratio
- `services`: revenue per client, payroll ratio, client concentration
- `freelancer` / `professional_practice`: income stability, expense ratio, runway
- `other`: common metrics only until business model is clarified

## Computation Runtime

- Use `scripts/compute_metrics.py` for metric computation.
- Use `scripts/render_report.py` to generate both report formats from `metrics_data.json`.
- If a `bank_csv` text blob is provided in JSON input, script normalizes it automatically.
- Keep parsing conservative; if a field is not reliably derivable, mark missing.

## Period Rules

- Default report period: latest completed calendar month.
- Trend metrics: require at least 3 months.
- YoY metrics and Rule of 40: require 13 monthly points or explicit YoY value.

## Source-Specific Guidance

- Bank CSV: include date, debit/credit (or signed amount), and balance columns.
- Stripe: export subscriptions + invoices/payments for the same date range.
- QBO/Xero: export monthly P&L; note whether values are cash or accrual basis.

## Output Contract

Always produce:

1. Inline metrics summary with label for each metric.
2. `financial_report.html` as the primary human-readable report.
3. `financial_report.md` as a fallback/plain-text version.
4. `metrics_data.json` with values, labels, and missing inputs.

Optional:

- `revenue_trend.png` only when charting support is available.

## Security & Privacy

- Run locally only.
- Do not include customer names/emails in output files.
- Preserve aggregate values and anonymized identifiers only.
