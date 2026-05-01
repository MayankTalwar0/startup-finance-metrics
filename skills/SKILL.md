---
name: startup-financial-analyst
description: >
  Financial health analysis for startups and small businesses. Ingests bank
  CSV, accounting exports, and pasted figures. Computes shared business
  metrics first, then adds a short industry section (SaaS, e-commerce,
  services, freelancer/consulting) when enough data exists.
metadata:
  version: "1.1.0"
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

- **Business type**: `saas`, `ecommerce`, `services`, `freelancer`, `professional_practice`, or `other`. If the user does not state it, infer from data and assign a confidence. If confidence is below ~80% (conflicting or weak signals), STOP and ask the user to confirm — and tell them specifically why you were uncertain. Only proceed silently when confidence is high; even then, state your inference and the signals briefly.
- **Business website** (optional): for product/service context to improve categorization
- **About the business** (optional): brief description of what they sell and who they serve
- **Financial data** (required): bank statement CSV, Stripe export, or pasted figures
- **Customer metrics** (optional): customer counts, churn rates, new/lost customers
- Analysis period: default to latest completed calendar month
- Data coverage: ask for 3 months minimum for trends, 13 months preferred for YoY metrics

## Core Behavior

1. Compute common metrics for every business:
   - Revenue, Expenses, Net Profit/Loss, Profit Margin
   - Net Cash Flow, Cash Balance, Runway (if burning)
   - Revenue Growth (if prior period exists)
2. Compute the 12 advanced investor metrics only when required fields exist.
3. Compute 2-3 industry-specific metrics when `business_type` is provided.
4. Never invent values. Missing inputs must return:
   - `label: insufficient_data`
   - `reason: Cannot be determined from the provided inputs.`
   - `missing_inputs: [...]`
5. When a metric is mathematically meaningless because the business is cash flow positive (e.g., Cash Runway, Burn Multiple when net burn ≤ 0), return:
   - `label: not_applicable`
   - `reason: Business is cash flow positive`
6. For multi-month input, call `computeFinancialMetrics` once per month, then call `generateFinancialReport` ONCE with a multi-month payload (`{"months": [...]}`). Produce a single unified report — never one file per month.

## Transaction Categorization Rules

When processing bank statements, the agent MAY use its judgment to categorize
transactions based on descriptions and business context:

- "AWS Cloud Hosting" → COGS (for SaaS)
- "Google Ads" → Sales & Marketing
- "Payroll" → Payroll expense
- "Stripe fees" → COGS (payment processing)

### Categorization Guardrails

1. **NEVER assume a percentage.** Do NOT say "COGS is ~15% of revenue". Every number must trace to a specific transaction line item.
2. **NEVER hardcode or invent numerical values.** If no transactions match a category, pass `null`.
3. **Categorization IS allowed.** Assigning a transaction to a category based on its description is not invention — it is classification.
4. **When uncertain**, return `null`. It is better to return `insufficient_data` than to fabricate a number.

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
- `ecommerce`: AOV (requires `total_orders`), ad-spend ratio, refund rate (requires `refund_amount`)
- `services`: revenue per client, payroll ratio (requires `payroll_spend`), client concentration (requires `top_client_revenue`)
- `freelancer` / `professional_practice`: expense ratio, effective hourly rate (requires `billable_hours`), runway
- `other`: common metrics only until business model is clarified

## Computation Runtime

- Use `computeFinancialMetrics` tool for metric computation.
- Use `generateFinancialReport` tool to generate both report formats and save to disk.
- If a `bank_csv` text blob is provided in JSON input, script normalizes it automatically (basic totals only — prefer pre-categorized inputs).
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

Always produce ONE unified report covering the full period the user supplied:

1. Inline metrics summary with label for each metric.
2. `financial_report.html` — single unified report covering all months (saved to disk).
3. `financial_report.md` — plain-text fallback of the same unified report (saved to disk).
4. `metrics_data.json` with values, labels, and missing inputs.
5. AI categorization disclaimer when transaction descriptions were used for classification.
6. Industry confidence + reasoning visible in the report header.

Do NOT produce per-month report files (e.g., `march_report.md`, `april_report.md`).

Optional:

- `revenue_trend.png` only when charting support is available.

## Security & Privacy

- Run locally only.
- Do not include customer names/emails in output files.
- Preserve aggregate values and anonymized identifiers only.
