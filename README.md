# startup-financial-analyst

Financial health analysis for startups and small businesses.

## Scope

Works across common business types:

- SaaS
- E-commerce
- Agencies and services firms
- Freelancers and consultants
- Professional practices

## What It Does

1. Ingests bank CSV, Stripe export CSV, QBO/Xero export CSV, or pasted values.
2. Computes common health metrics first.
3. Computes advanced metrics only when required fields are present.
4. Returns `insufficient_data` with `missing_inputs` instead of inventing values.
5. Adds 2-3 industry-focused metrics based on business type.

## Analysis Period

- Default: latest completed calendar month.
- Trend metrics: 3 months minimum.
- YoY metrics: 13 monthly points preferred.

## Metrics Reference

The skill computes metrics only when the required inputs are present. If a metric cannot be supported by the uploaded data, it returns `insufficient_data` with the exact missing fields instead of guessing.

| # | Metric | What it explains | Formula | Required inputs |
|---|---|---|---|---|
| 1 | Net Burn | How much cash the business is losing or generating in the period. | `monthly_opex - monthly_revenue` | `monthly_opex`, `monthly_revenue` |
| 2 | Runway | How many months of cash remain at the current burn rate. | `current_cash / net_burn` | `current_cash`, positive `net_burn` |
| 3 | Gross Margin | How much revenue remains after direct delivery/product costs. | `(monthly_revenue - cogs) / monthly_revenue * 100` | `monthly_revenue`, `cogs` |
| 4 | CAC | Average cost to acquire one new customer. | `sales_marketing_spend / new_customers` | `sales_marketing_spend`, `new_customers` |
| 5 | LTV | Estimated lifetime gross profit from a customer. | `(ARPU * gross_margin) / logo_churn_rate` | `monthly_revenue`, `active_customers`, `lost_customers`, `cogs` |
| 6 | LTV:CAC | Whether acquisition economics are healthy. | `ltv / cac` | Computable `ltv`, computable `cac` |
| 7 | Revenue Growth | Period-over-period revenue growth. | `(monthly_revenue - prev_monthly_revenue) / prev_monthly_revenue * 100` | `monthly_revenue`, `prev_monthly_revenue` |
| 8 | Logo Churn | Share of customers lost during the period. | `lost_customers / active_customers * 100` | `lost_customers`, `active_customers` |
| 8 | Revenue Churn | Share of starting recurring revenue lost to churn. | `churned_mrr / starting_mrr * 100` | `churned_mrr`, `starting_mrr` |
| 9 | Burn Multiple | Cash burned for each dollar of net new ARR. | `net_burn / (arr_end - arr_start)` | `monthly_opex`, `monthly_revenue`, `arr_start`, `arr_end` |
| 10 | NRR | Whether existing recurring revenue expands or contracts. | `(starting_mrr + expansion_mrr - churned_mrr - contraction_mrr) / starting_mrr * 100` | `starting_mrr`, `expansion_mrr`, `churned_mrr`, `contraction_mrr` |
| 11 | Rule of 40 | Growth plus profitability balance. | `revenue_growth_yoy_pct + operating_margin_pct` | `revenue_growth_yoy_pct`, `operating_margin_pct` |
| 12 | CAC Payback | Months needed to recover CAC through gross profit. | `cac / (ARPU * gross_margin)` | Computable `cac`, `monthly_revenue`, `active_customers`, computable `gross_margin` |

Supporting definitions:

- `ARPU = monthly_revenue / active_customers`
- `gross_margin = (monthly_revenue - cogs) / monthly_revenue`
- `net_burn = monthly_opex - monthly_revenue`

Industry-specific sections stay intentionally small. SaaS usually gets MRR/ARR, churn/NRR, and CAC payback or LTV:CAC. E-commerce usually gets gross margin, AOV, and ad/refund ratio when order data exists. Services and freelancers usually get revenue per client, expense ratio, income stability, and runway when the required data exists.

## Supported Inputs

- Bank transaction CSV
- Stripe subscriptions/invoices/payments CSV exports
- Xero / QuickBooks monthly P&L CSV export
- Inline pasted numbers

## Integration Note

For Stripe, QBO, and Xero, this skill expects exported files. It does not pull live API data or require credentials.

## Output

- Inline summary table
- `financial_report.html` (primary, polished view)
- `financial_report.md` (fallback/plain-text view)
- `metrics_data.json`
- Optional chart image when charting support exists

## Runtime

- Python 3.8+
- Standard library only for parser and metric engine

## License

MIT

## Built By SlickBooks

Built by Mayank, founder of [SlickBooks](https://slickbooks.online).

SlickBooks provides managed bookkeeping, bookkeeping automation, financial forecast automation, and custom finance agents.

All analysis in this skill runs locally from user-provided files. Financial data is not sent to SlickBooks or any external service by this skill.
