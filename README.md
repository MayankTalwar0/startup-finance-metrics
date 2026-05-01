# Startup Finance Metrics (MCP Server)

An MCP (Model Context Protocol) server for analyzing startup financial health and generating metrics reports locally.

> **🔒 PRIVACY & SECURITY FIRST:**
> - **Zero Cloud Risk**: This tool runs 100% locally on your machine/server.
> - **No Data Sent Externally**: Financial data is **NEVER** sent to any external API, cloud provider, or third-party service (including SlickBooks).
> - **No Data Storage**: The server processes inputs in-memory and returns the metrics directly to the MCP client. No data is stored, cached, or logged.
> - **Strictly Read-Only**: This server executes NO financial state changes. It is a strictly read-only mathematical engine.
> - **Strictly Local Processing**: Safely integrates with Claude Desktop, Cursor, Glama, and other MCP clients while maintaining full data sovereignty over your sensitive financial inputs.

## Why This Exists

If you're a startup founder raising funds or preparing for a board meeting, investors will ask you for metrics like MRR, burn rate, gross margin, LTV:CAC, and runway — often on short notice. Most founders either don't track these consistently, or spend hours pulling numbers from bank statements and spreadsheets before every fundraise.

This tool turns your raw bank statement (or Stripe/QBO export) into a structured financial metrics report in minutes, entirely on your own machine. No accountant required for a first pass. No sensitive data leaving your computer.

## What It Does

1. **Ingests Data**: Accepts bank CSVs, Stripe export CSVs, QBO/Xero export CSVs, or pasted values. *(For best results, provide a minimum 3-month bank statement and active user stats. Sample files are available in the `test/` folder).*
2. **AI Transaction Categorization**: The AI classifies each bank transaction into revenue, COGS, S&M, payroll, or G&A based on the description. **This step is AI-driven and can make mistakes** — e.g. misclassifying a contractor payment as payroll vs. COGS, or missing an ambiguous line item. Always review the categorizations before sharing results with investors.
3. **Computes Key Metrics**: Calculates Net Burn, Runway, Gross Margin, CAC, LTV, Rule of 40, and more — across one or multiple months in a single comparative report.
4. **Strict Validation**: Returns `insufficient_data` with `missing_inputs` instead of hallucinating values. If data is missing or ambiguous, the engine tells you what's needed rather than guessing.
5. **Generates Reports**: Creates clean, formatted Markdown and HTML reports — one unified report covering all months supplied, with side-by-side period comparison.

## Setup & Installation

### Option 1: Automated Installation (Claude Desktop, Cursor, Windsurf)

If you have Node.js installed on your computer, you can use the Smithery CLI to automatically inject the configuration for you:

```bash
npx -y @smithery/cli install @MayankTalwar0/startup-finance-metrics --client claude
```
*(Note: You can change `--client claude` to `--client cursor` or `--client windsurf` depending on your app).*

### Option 2: Claude Desktop (Manual Installation for Non-Developers)

Since this tool runs entirely on your own machine to protect your financial data, it requires a one-time manual setup. 
**Good News:** You do **NOT** need to have Python installed! The tool we use below (`uv`) will automatically download everything it needs invisibly in the background.

**Step 1: Install `uv`**
This server uses `uv` (a fast Python manager) to run locally. If you don't have it installed:
- **Mac/Linux**: Open your Terminal and run: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Windows**: Open PowerShell and run: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

**Step 2: Open Claude's Configuration**
1. Open the Claude Desktop App.
2. In the top left menu, click **Claude** -> **Settings** (or Preferences).
3. Click on the **Developer** tab in the left sidebar.
4. Click the **Edit Config** button. This will open a file named `claude_desktop_config.json` in your default text editor.

**Step 3: Add the Server**
Replace the contents of that file with the following code (if you already have other servers, just add the `startup-finance-metrics` block inside your existing `mcpServers`):

```json
{
  "mcpServers": {
    "startup-finance-metrics": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/MayankTalwar0/startup-finance-metrics.git",
        "startup-finance-mcp"
      ]
    }
  }
}
```

**Step 4: Restart Claude**
Save the file, close it, and completely restart Claude Desktop. You will now see a new "hammer" (Tools) icon in your Claude chats!

### Option 3: Claude Code, Glama, or Custom Cursor setup

For CLI agents like Claude Code, or if you prefer to manually configure Glama and Cursor, use the `uvx` command:

**For Claude Code:**
```bash
claude mcp add startup-finance -- uvx --from git+https://github.com/MayankTalwar0/startup-finance-metrics.git startup-finance-mcp
```

**For Glama / Cursor (Custom MCP config):**
```bash
uvx --from git+https://github.com/MayankTalwar0/startup-finance-metrics.git startup-finance-mcp
```

### Option 4: Local Development

```bash
git clone https://github.com/MayankTalwar0/startup-finance-metrics.git
cd startup-finance-metrics
pip install -e .

# Run the server directly
startup-finance-mcp
```

## Available MCP Tools

This server provides the following tools to the MCP client:

1. `computeFinancialMetrics(inputs_json: str)`: Computes startup financial metrics (runway, gross margin, CAC, LTV, etc.) from structured inputs. Called once per month when analyzing multi-month data.
2. `generateFinancialReport(metrics_json: str, output_dir: str)`: Renders a unified HTML + Markdown report. Accepts either a single-month payload or a multi-month `{"months": [...]}` payload — producing one comparative report across all periods supplied.

## Using as a Standalone AI Skill

If you don't want to use the full MCP server and just want a simple prompt to use in tools like Claude Code or OpenClaw, you can find the raw skill prompt in [`skills/SKILL.md`](skills/SKILL.md).

## Metrics Reference

| # | Metric | Formula | Required inputs |
|---|---|---|---|
| 1 | Net Burn | `monthly_opex - monthly_revenue` | `monthly_opex`, `monthly_revenue` |
| 2 | Runway | `current_cash / net_burn` | `current_cash`; requires `net_burn > 0` (else returns `not_applicable: business is cash flow positive`) |
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
