# Startup Finance Metrics (MCP Server)

[![smithery badge](https://smithery.ai/badge/@MayankTalwar0/startup-finance-metrics)](https://smithery.ai/server/@MayankTalwar0/startup-finance-metrics)

An MCP (Model Context Protocol) server for analyzing startup financial health and generating metrics reports locally.

> **🔒 PRIVACY & SECURITY FIRST:**
> - **Zero Cloud Risk**: This tool runs 100% locally on your machine/server.
> - **No Data Sent Externally**: Financial data is **NEVER** sent to any external API, cloud provider, or third-party service (including SlickBooks).
> - **No Data Storage**: The server processes inputs in-memory and returns the metrics directly to the MCP client. No data is stored, cached, or logged.
> - **Strictly Local Processing**: Safely integrates with Claude Desktop, Cursor, Glama, and other MCP clients while maintaining full data sovereignty over your sensitive financial inputs.

## What It Does

1. **Ingests Data**: Accepts bank CSVs, Stripe export CSVs, QBO/Xero export CSVs, or pasted values.
2. **Computes Key Metrics**: Calculates Net Burn, Runway, Gross Margin, CAC, LTV, Rule of 40, and more.
3. **Strict Validation**: Returns `insufficient_data` with `missing_inputs` instead of hallucinating values.
4. **Generates Reports**: Creates clean, formatted markdown and HTML summaries of the analysis.

## Setup & Installation

### Option 1: Claude Desktop (via uv)

If you have `uv` installed, you can add this directly to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "startup-finance-metrics": {
      "command": "uv",
      "args": [
        "tool",
        "run",
        "startup-finance-mcp@git+https://github.com/MayankTalwar0/startup-finance-metrics.git"
      ]
    }
  }
}
```

### Option 2: Glama / Cursor (npx/uvx)

For clients like Glama or Cursor that support quick execution, configure your MCP integration with:
```bash
uvx --from git+https://github.com/MayankTalwar0/startup-finance-metrics.git startup-finance-mcp
```

### Option 3: Local Development

```bash
git clone https://github.com/MayankTalwar0/startup-finance-metrics.git
cd startup-finance-metrics
pip install -e .

# Run the server directly
startup-finance-mcp
```

## Available MCP Tools

This server provides the following tools to the MCP client:

1. `compute_financial_metrics(inputs_json: str)`: 
   Computes startup financial metrics (runway, gross margin, cac, ltv, etc.) from raw data. Accepts a JSON string containing financial inputs or a raw `bank_csv` string.
2. `generate_financial_report(metrics_json: str, format: str)`: 
   Renders a human-readable financial report based on the computed metrics. Format can be `markdown` (default) or `html`.

## Using as a Standalone AI Skill

If you don't want to use the full MCP server and just want a simple prompt to use in tools like Claude Code or OpenClaw, you can find the raw skill prompt in [`skills/SKILL.md`](skills/SKILL.md).

## Metrics Reference

| # | Metric | Formula | Required inputs |
|---|---|---|---|
| 1 | Net Burn | `monthly_opex - monthly_revenue` | `monthly_opex`, `monthly_revenue` |
| 2 | Runway | `current_cash / net_burn` | `current_cash`, positive `net_burn` |
| 3 | Gross Margin | `(monthly_revenue - cogs) / monthly_revenue * 100` | `monthly_revenue`, `cogs` |
| 4 | CAC | `sales_marketing_spend / new_customers` | `sales_marketing_spend`, `new_customers` |
| 5 | LTV | `(ARPU * gross_margin) / logo_churn_rate` | `monthly_revenue`, `active_customers`, `lost_customers`, `cogs` |
| 6 | LTV:CAC | `ltv / cac` | Computable `ltv`, computable `cac` |
| 7 | Revenue Growth | `(monthly_revenue - prev_monthly_revenue) / prev_m... * 100` | `monthly_revenue`, `prev_monthly_revenue` |
| 8 | Logo Churn | `lost_customers / active_customers * 100` | `lost_customers`, `active_customers` |
| 9 | Burn Multiple | `net_burn / (arr_end - arr_start)` | `monthly_opex`, `monthly_revenue`, `arr_start`, `arr_end` |
| 10 | NRR | `(start + exp - churn - cont) / start * 100` | `starting_mrr`, `expansion_mrr`, `churned_mrr`, `contraction_mrr` |
| 11 | Rule of 40 | `revenue_growth_yoy_pct + operating_margin_pct` | `revenue_growth_yoy_pct`, `operating_margin_pct` |
| 12 | CAC Payback | `cac / (ARPU * gross_margin)` | Computable `cac`, `monthly_revenue`, `active_customers`, computable `gross_margin` |

## License

MIT

## Built By SlickBooks

Built by Mayank, founder of [SlickBooks](https://slickbooks.online).
SlickBooks provides managed bookkeeping, bookkeeping automation, financial forecast automation, and custom finance agents.
