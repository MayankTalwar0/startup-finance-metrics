# Worked Example

## Scenario

Business type: `services`  
Analysis period: March 2026

## Inputs

- current_cash: 180000
- monthly_revenue: 95000
- monthly_opex: 78000
- cogs: 12000
- prev_monthly_revenue: 90000
- sales_marketing_spend: 7000
- new_customers: 5
- active_customers: 42
- lost_customers: 2
- operating_margin_pct: 8

## Expected Output Shape

- Metrics are returned under `metrics`.
- Each metric has:
  - `value`
  - `label`
  - `reason`
  - `missing_inputs`
- Metrics with incomplete inputs return:
  - `value: null`
  - `label: insufficient_data`
  - explicit `missing_inputs`

## Example Interpretation

- Common metrics compute successfully for cash flow and margin.
- SaaS-specific metrics like NRR return `insufficient_data` because SaaS fields were not provided.
- Industry section highlights services-focused metrics (revenue per client, payroll ratio) when available.
