from mcp.server.fastmcp import FastMCP
import json
import logging
from pathlib import Path

from .compute_metrics import compute_all
from .render_report import render_markdown, render_html

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("startup_finance_mcp")

# Initialize FastMCP server
mcp = FastMCP(
    "Startup Finance Metrics",
    dependencies=["mcp"]
)

# Set up paths to resources
PROJECT_ROOT = Path(__file__).parent.parent.parent
REFERENCES_DIR = PROJECT_ROOT / "references"

@mcp.resource("file://references/coaching_templates.md")
def get_coaching_templates() -> str:
    """Provides financial coaching templates and advice rules."""
    path = REFERENCES_DIR / "coaching_templates.md"
    return path.read_text(encoding="utf-8") if path.exists() else "Coaching templates not found."

@mcp.resource("file://references/validation_rules.md")
def get_validation_rules() -> str:
    """Provides strict validation rules for the metrics engine."""
    path = REFERENCES_DIR / "validation_rules.md"
    return path.read_text(encoding="utf-8") if path.exists() else "Validation rules not found."

@mcp.resource("file://references/worked_example.md")
def get_worked_example() -> str:
    """Provides a worked example of financial metric computation."""
    path = REFERENCES_DIR / "worked_example.md"
    return path.read_text(encoding="utf-8") if path.exists() else "Worked example not found."

@mcp.prompt()
def analyzeFinances() -> str:
    """
    Prompt template to analyze startup finances like an expert CFO.
    """
    return '''You are an expert Startup CFO and Financial Analyst.

## Step 1: Gather Information

Ask the user to provide the following. Be friendly and concise:

**Required:**
- Bank statement CSV (or Stripe export, Xero/QBO P&L export)

**Optional (improves accuracy):**
- Business industry: `saas`, `ecommerce`, `services`, `freelancer`, `professional_practice`, or `other`
- Business website URL (for context on the product/service)
- Brief description of the business (what they sell, who they serve)
- Customer metrics CSV (customer counts, churn rates, new/lost customers)

## Step 1b: Determine Business Type (industry confidence gate)

Before computing, you MUST establish `business_type`. Use this decision rule:

1. If the user explicitly states the industry, use it.
2. Otherwise, infer from the data (transaction descriptions, revenue model signals like MRR/ARR, customer churn columns, AOV/orders, billable hours, top-client concentration, etc.) and assign yourself a confidence:
   - **high (≥80%)**: Multiple strong, consistent signals point to one industry. Proceed without blocking, but state the inference and the signals you used in one sentence.
   - **medium / low (<80%)**: Conflicting or weak signals. STOP and ask the user to confirm the industry. Tell them specifically what made you uncertain (e.g., "I see recurring monthly revenue which suggests SaaS, but I also see large per-order variability which could indicate ecommerce").
3. Record `industry_confidence` ("high" | "medium" | "low") and `industry_reasoning` (one sentence explaining the choice or the uncertainty). Both will be passed to `generateFinancialReport`.

Never silently assume an industry. Either be transparent (high confidence + stated reasoning) or block and ask (medium/low).

## Step 2: Categorize Transactions

When you receive bank/financial data, categorize EACH transaction using your judgment and the business context. Assign transactions to these expense categories:

- **Revenue**: Subscription payments, client payments, product sales, interest income
- **COGS**: Direct costs to deliver the product/service (use industry context):
  - SaaS: cloud hosting (AWS/Azure/GCP), payment processing fees, CDN, monitoring
  - Ecommerce: inventory, shipping, fulfillment, packaging, payment fees
  - Services: subcontractor payments for client deliverables, direct materials
- **Sales & Marketing (S&M)**: Ad spend (Google/Facebook/LinkedIn Ads), affiliate payouts, marketing SaaS tools
- **Payroll**: Salary/wage payments, contractor payments (unless directly COGS)
- **G&A**: Rent, legal, accounting, bank fees, insurance, internal tools/subscriptions
- **Exclude**: Internal transfers between own accounts (reserve transfers)
- **Refunds**: Subtract from revenue, do not count as expenses

### CRITICAL RULES:
1. **NEVER assume a percentage.** Do NOT estimate any value as a fraction of another (e.g., "COGS ~ 15% of revenue"). Every number must trace to a specific transaction.
2. **NEVER hardcode or invent numbers.** If no transactions belong to a category, pass `null`. Do NOT estimate.
3. **Categorization IS allowed.** You MAY assign "AWS Cloud Hosting" to COGS or "Google Ads" to S&M based on description.
4. **When uncertain**, pass `null`. It is better to return `insufficient_data` than to fabricate a number.

## Step 3: Compute Metrics

Sum categorized transactions and call `computeFinancialMetrics` with structured JSON. Pass `null` for anything you cannot determine from the actual data.

For multi-month data, call `computeFinancialMetrics` once per month with that month's values, but DO NOT generate a separate report per month.

## Step 4: Generate ONE Unified Report

Call `generateFinancialReport` exactly ONCE, with a single payload covering every month the user supplied.

- For single-month data, pass the `computeFinancialMetrics` output directly.
- For multi-month data, build the multi-month payload shape:
  ```json
  {
    "source": "bank_csv_categorized",
    "business_type": "saas",
    "industry_confidence": "high",
    "industry_reasoning": "Recurring MRR column and SaaS-style churn metrics in customer CSV.",
    "period_label": "March 2026 – May 2026",
    "months": [
      {"period": "March 2026", ...March computeFinancialMetrics output},
      {"period": "April 2026", ...April computeFinancialMetrics output},
      {"period": "May 2026",   ...May computeFinancialMetrics output}
    ]
  }
  ```

This saves BOTH:
- `financial_report.html` — styled report, open in any browser
- `financial_report.md` — plain-text fallback

Never produce per-month report files like `march_report.md`. One unified report only.

Read `file://references/coaching_templates.md` for investor coaching advice based on metric labels.

## Step 5: Present Results

1. Show an inline summary of key metrics.
2. Tell the user both report files were saved and their paths.
3. If any metrics used AI-categorized transactions, add this disclaimer:
   > **AI Categorization Notice:** Some metrics were derived from AI-categorized bank transactions. Only explicitly identified line items were summed — no percentage-based estimates were used. Please review categorizations for accuracy.
4. List any `insufficient_data` metrics and what additional data would unlock them.

Always rely on the `computeFinancialMetrics` tool rather than doing math yourself. Never invent values for missing data.'''

@mcp.tool()
def computeFinancialMetrics(inputs_json: str) -> str:
    """
    Computes startup financial metrics from structured data.

    Args:
        inputs_json: A JSON string containing financial inputs. Preferred: pre-categorized
                     values like 'monthly_revenue', 'monthly_opex', 'cogs',
                     'sales_marketing_spend', 'business_type', etc.
                     Also accepts a raw 'bank_csv' blob as fallback (basic totals only).
    Returns:
        JSON string containing computed metrics and missing inputs diagnostics.
    """
    try:
        inputs = json.loads(inputs_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse inputs_json: {e}")
        return json.dumps({"error": f"Invalid JSON input: {e}"})

    result = compute_all(inputs)
    return json.dumps(result, indent=2)

@mcp.tool()
def generateFinancialReport(metrics_json: str, output_dir: str = ".") -> str:
    """
    Generates a single unified HTML + Markdown financial report and saves them to disk.

    Args:
        metrics_json: JSON string. Two accepted shapes:
          1. Single-month: the direct output from `computeFinancialMetrics`.
          2. Multi-month (preferred when user supplies multiple months of data):
             {
               "source": "...",
               "business_type": "saas",
               "industry_confidence": "high|medium|low",
               "industry_reasoning": "Why this industry was chosen, or why uncertain.",
               "period_label": "March 2026 – May 2026",
               "months": [
                 {"period": "March 2026", ...computeFinancialMetrics output for March},
                 {"period": "April 2026", ...computeFinancialMetrics output for April},
                 {"period": "May 2026",   ...computeFinancialMetrics output for May}
               ]
             }
          Always produce ONE unified report covering all months the user supplied.
          Do NOT generate one report per month.
        output_dir: Directory to save reports to. Default is current directory.
    Returns:
        JSON with paths to both report files and the markdown content inline.
    """
    try:
        payload = json.loads(metrics_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse metrics_json: {e}")
        return json.dumps({"error": f"Invalid JSON input: {e}"})

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    md_content = render_markdown(payload)
    html_content = render_html(payload)

    md_path = out / "financial_report.md"
    html_path = out / "financial_report.html"

    md_path.write_text(md_content, encoding="utf-8")
    html_path.write_text(html_content, encoding="utf-8")

    logger.info(f"Reports saved: {md_path.resolve()}, {html_path.resolve()}")

    return json.dumps({
        "md_path": str(md_path.resolve()),
        "html_path": str(html_path.resolve()),
        "markdown_content": md_content,
    })

if __name__ == "__main__":
    mcp.run()
