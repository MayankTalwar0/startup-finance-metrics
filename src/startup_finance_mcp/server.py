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
A user wants you to analyze their financial data.
Your process:
1. Ask the user for their financial data (bank CSV, Stripe export, or simple numbers like monthly_opex, monthly_revenue).
2. If the user provides data, use the `computeFinancialMetrics` tool to process it.
3. Read the `file://references/coaching_templates.md` resource to understand how to provide industry-specific advice based on the metrics.
4. Finally, use the `generateFinancialReport` tool to create a clear markdown report for the user, and append your expert coaching advice below it.
Always rely on the `computeFinancialMetrics` tool rather than doing math yourself. If data is insufficient, tell the user exactly what missing inputs are needed.'''

@mcp.tool()
def computeFinancialMetrics(inputs_json: str) -> str:
    """
    Computes startup financial metrics (runway, gross margin, cac, ltv, etc.) from raw data.
    
    Args:
        inputs_json: A JSON string containing financial inputs. Can include individual values like
                     'monthly_opex', 'monthly_revenue', 'current_cash' OR a 'bank_csv' string containing 
                     bank transaction rows (deposit, withdrawal, amount).
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
def generateFinancialReport(metrics_json: str, format: str = "markdown") -> str:
    """
    Renders a human-readable financial report based on the computed metrics.
    
    Args:
        metrics_json: The JSON string output from `computeFinancialMetrics`.
        format: "markdown" or "html". Default is "markdown".
    Returns:
        The formatted financial report as a string.
    """
    try:
        payload = json.loads(metrics_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse metrics_json: {e}")
        return f"Error: Invalid JSON input: {e}"
        
    if format.lower() == "html":
        return render_html(payload)
    return render_markdown(payload)

if __name__ == "__main__":
    mcp.run()
