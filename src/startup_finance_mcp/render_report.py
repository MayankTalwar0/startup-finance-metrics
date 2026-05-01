"""
Render financial reports in both Markdown and HTML from metrics JSON.

Usage:
    python scripts/render_report.py --input metrics_data.json
"""
import argparse
import json
from datetime import UTC, datetime
from html import escape
from pathlib import Path


METRIC_LABELS = {
    "1_net_burn": "1. Net Burn",
    "2_runway": "2. Cash Runway",
    "3_gross_margin": "3. Gross Margin",
    "4_cac": "4. CAC",
    "5_ltv": "5. LTV",
    "6_ltv_cac": "6. LTV:CAC",
    "7_revenue_growth": "7. Revenue Growth",
    "8_churn_logo": "8. Churn (Logo)",
    "8_churn_revenue": "8. Churn (Revenue)",
    "9_burn_multiple": "9. Burn Multiple",
    "10_nrr": "10. NRR",
    "11_rule_of_40": "11. Rule of 40",
    "12_cac_payback": "12. CAC Payback",
}

INDUSTRY_METRIC_LABELS = {
    # SaaS
    "ind_mrr": "MRR (Monthly Recurring Revenue)",
    "ind_arr": "ARR (Annual Recurring Revenue)",
    # Ecommerce
    "ind_aov": "AOV (Average Order Value)",
    "ind_ad_spend_ratio": "Ad Spend Ratio",
    "ind_refund_rate": "Refund Rate",
    # Services
    "ind_revenue_per_client": "Revenue Per Client",
    "ind_payroll_ratio": "Payroll Ratio",
    "ind_client_concentration": "Client Concentration",
    # Freelancer / Professional Practice
    "ind_expense_ratio": "Expense Ratio",
    "ind_effective_hourly_rate": "Effective Hourly Rate",
}

INDUSTRY_DISPLAY_NAMES = {
    "saas": "SaaS",
    "ecommerce": "E-Commerce",
    "services": "Services",
    "freelancer": "Freelancer",
    "professional_practice": "Professional Practice",
    "other": "General",
}


def _fmt_value(value, label=None):
    if value is None:
        if label == "not_applicable":
            return "N/A"
        return "Cannot be determined"
    if isinstance(value, (int, float)):
        return f"{value:,.2f}"
    return str(value)


def _build_rows(metrics):
    def _sort_key(metric_key):
        parts = metric_key.split("_", 1)
        try:
            idx = int(parts[0])
        except ValueError:
            idx = 999
        return (idx, metric_key)

    rows = []
    for key in sorted(metrics.keys(), key=_sort_key):
        item = metrics[key]
        rows.append(
            {
                "metric_id": key,
                "metric_name": METRIC_LABELS.get(key, key.replace("_", " ").title()),
                "value": _fmt_value(item.get("value"), item.get("label")),
                "label": item.get("label", ""),
                "reason": item.get("reason", ""),
                "missing": ", ".join(item.get("missing_inputs", [])),
            }
        )
    return rows


def _build_industry_rows(industry_metrics):
    rows = []
    for key in sorted(industry_metrics.keys()):
        item = industry_metrics[key]
        rows.append(
            {
                "metric_id": key,
                "metric_name": INDUSTRY_METRIC_LABELS.get(key, key.replace("_", " ").title()),
                "value": _fmt_value(item.get("value"), item.get("label")),
                "label": item.get("label", ""),
                "reason": item.get("reason", ""),
                "missing": ", ".join(item.get("missing_inputs", [])),
            }
        )
    return rows


AI_DISCLAIMER = (
    "> **⚠️ AI Categorization Notice:** Some metrics in this report may have been "
    "derived from AI-categorized bank transactions. Transaction categorization "
    "(e.g., identifying cloud hosting as COGS or ad spend as S&M) was based on "
    "description matching and business context. No percentage-based estimates or "
    "hardcoded assumptions were used — only explicitly identified line items were "
    "summed. Please review categorizations for accuracy."
)


def _is_multi_month(payload):
    return isinstance(payload.get("months"), list) and len(payload.get("months", [])) > 0


def _collect_metric_keys(months, field):
    keys = []
    seen = set()
    for m in months:
        for k in (m.get(field) or {}).keys():
            if k not in seen:
                seen.add(k)
                keys.append(k)

    def _sort_key(metric_key):
        parts = metric_key.split("_", 1)
        try:
            idx = int(parts[0])
        except ValueError:
            idx = 999
        return (idx, metric_key)

    return sorted(keys, key=_sort_key)


def render_markdown_multi(payload):
    months = payload.get("months", [])
    source = payload.get("source") or (months[0].get("source") if months else "manual")
    business_type = payload.get("business_type") or (months[0].get("business_type") if months else "other")
    industry_name = INDUSTRY_DISPLAY_NAMES.get(business_type, business_type.title())
    period_label = payload.get("period_label") or f"{months[0].get('period','?')} – {months[-1].get('period','?')}"
    industry_confidence = payload.get("industry_confidence")
    industry_reasoning = payload.get("industry_reasoning")

    period_headers = [m.get("period", f"M{i+1}") for i, m in enumerate(months)]

    lines = []
    lines.append("# Financial Report")
    lines.append("")
    lines.append(f"- Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"- Source: {source}")
    lines.append(f"- Industry: {industry_name}")
    if industry_confidence is not None:
        lines.append(f"- Industry confidence: {industry_confidence}")
    if industry_reasoning:
        lines.append(f"- Industry reasoning: {industry_reasoning}")
    lines.append(f"- Period: {period_label} ({len(months)} months)")
    lines.append("")
    lines.append(AI_DISCLAIMER)
    lines.append("")

    core_keys = _collect_metric_keys(months, "metrics")
    if core_keys:
        lines.append("## Core Metrics")
        lines.append("")
        header = "| Metric | " + " | ".join(period_headers) + " | Latest Label |"
        sep = "|---|" + "|".join(["---:"] * len(period_headers)) + "|---|"
        lines.append(header)
        lines.append(sep)
        for key in core_keys:
            name = METRIC_LABELS.get(key, key.replace("_", " ").title())
            cells = []
            latest_label = ""
            for m in months:
                item = (m.get("metrics") or {}).get(key, {})
                cells.append(_fmt_value(item.get("value"), item.get("label")))
                latest_label = item.get("label", latest_label)
            lines.append(f"| {name} | " + " | ".join(cells) + f" | {latest_label} |")
        lines.append("")

    industry_keys = _collect_metric_keys(months, "industry_metrics")
    if industry_keys:
        lines.append(f"## {industry_name} Industry Metrics")
        lines.append("")
        header = "| Metric | " + " | ".join(period_headers) + " | Latest Label |"
        sep = "|---|" + "|".join(["---:"] * len(period_headers)) + "|---|"
        lines.append(header)
        lines.append(sep)
        for key in industry_keys:
            name = INDUSTRY_METRIC_LABELS.get(key, key.replace("_", " ").title())
            cells = []
            latest_label = ""
            for m in months:
                item = (m.get("industry_metrics") or {}).get(key, {})
                cells.append(_fmt_value(item.get("value"), item.get("label")))
                latest_label = item.get("label", latest_label)
            lines.append(f"| {name} | " + " | ".join(cells) + f" | {latest_label} |")
        lines.append("")

    return "\n".join(lines)


def render_html_multi(payload):
    months = payload.get("months", [])
    source = escape(str(payload.get("source") or (months[0].get("source") if months else "manual")))
    business_type = payload.get("business_type") or (months[0].get("business_type") if months else "other")
    industry_name = escape(INDUSTRY_DISPLAY_NAMES.get(business_type, business_type.title()))
    period_label = escape(payload.get("period_label") or f"{months[0].get('period','?')} – {months[-1].get('period','?')}")
    industry_confidence = payload.get("industry_confidence")
    industry_reasoning = payload.get("industry_reasoning")
    period_headers = [m.get("period", f"M{i+1}") for i, m in enumerate(months)]

    def _build_table(field, labels_dict):
        keys = _collect_metric_keys(months, field)
        if not keys:
            return ""
        head_cells = "".join(f"<th style='text-align:right'>{escape(p)}</th>" for p in period_headers)
        rows_html = []
        for key in keys:
            name = labels_dict.get(key, key.replace("_", " ").title())
            cells = []
            latest_label = ""
            for m in months:
                item = (m.get(field) or {}).get(key, {})
                val = _fmt_value(item.get("value"), item.get("label"))
                cells.append(f"<td class='num'>{escape(val)}</td>")
                latest_label = item.get("label", latest_label)
            label_cls = f"label {latest_label}" if latest_label else "label"
            rows_html.append(
                f"<tr><td>{escape(name)}</td>{''.join(cells)}"
                f"<td><span class='{label_cls}'>{escape(latest_label)}</span></td></tr>"
            )
        return (
            "<thead><tr><th>Metric</th>" + head_cells + "<th>Latest Label</th></tr></thead>"
            "<tbody>" + "".join(rows_html) + "</tbody>"
        )

    core_table = _build_table("metrics", METRIC_LABELS)
    industry_table = _build_table("industry_metrics", INDUSTRY_METRIC_LABELS)

    industry_section = ""
    if industry_table:
        industry_section = (
            f"<div class='section-head'><h2>{industry_name} Industry Metrics</h2></div>"
            f"<table>{industry_table}</table>"
        )

    industry_meta = ""
    if industry_confidence is not None:
        industry_meta += f" | Industry confidence: {escape(str(industry_confidence))}"
    if industry_reasoning:
        industry_meta += f"<br><span style='color:var(--muted)'>Industry reasoning: {escape(str(industry_reasoning))}</span>"

    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Financial Report</title>
  <style>
    :root {{
      --bg: #0b1220; --panel: #111a2b; --panel-2: #0f1726;
      --text: #e5edf8; --muted: #9fb1c9; --line: #243247;
      --strong: #2dd4bf; --adequate: #60a5fa; --weak: #f59e0b;
      --critical: #ef4444; --insufficient_data: #a3a3a3;
      --not_applicable: #a3a3a3; --accent: #818cf8;
    }}
    body {{ margin:0; font-family:"Segoe UI",Arial,sans-serif; background:var(--bg); color:var(--text); }}
    .wrap {{ max-width: 1200px; margin: 24px auto; padding: 0 16px; }}
    .panel {{ background: var(--panel); border:1px solid var(--line); border-radius:8px; overflow:hidden; box-shadow:0 14px 36px rgba(0,0,0,0.45); margin-bottom:20px; }}
    .head {{ padding:16px; border-bottom:1px solid var(--line); }}
    .section-head {{ padding:12px 16px; border-bottom:1px solid var(--line); background:var(--panel-2); }}
    .section-head h2 {{ margin:0; font-size:16px; color:var(--accent); }}
    h1 {{ margin:0 0 4px; font-size:24px; }}
    .meta {{ color:var(--muted); font-size:13px; }}
    .disclaimer {{ padding:12px 16px; background:rgba(245,158,11,0.08); border-left:3px solid var(--weak); font-size:12px; color:var(--muted); line-height:1.5; }}
    table {{ width:100%; border-collapse: collapse; }}
    th, td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:13px; }}
    th {{ background:var(--panel-2); font-weight:600; }}
    td.num {{ text-align:right; font-variant-numeric: tabular-nums; }}
    .label {{ display:inline-block; border-radius:999px; padding:2px 8px; font-size:12px; border:1px solid currentColor; line-height:1.4; }}
    .strong {{ color: var(--strong); }} .adequate {{ color: var(--adequate); }}
    .weak {{ color: var(--weak); }} .critical {{ color: var(--critical); }}
    .insufficient_data {{ color: var(--insufficient_data); }}
    .not_applicable {{ color: var(--not_applicable); }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      <div class="head">
        <h1>Financial Report</h1>
        <div class="meta">Generated: {escape(generated)} | Source: {source} | Industry: {industry_name} | Period: {period_label}{industry_meta}</div>
      </div>
      <div class="disclaimer">
        ⚠️ <strong>AI Categorization Notice:</strong> Some metrics may have been derived from
        AI-categorized bank transactions. Only explicitly identified line items were summed —
        no percentage-based estimates or hardcoded assumptions were used. Please review
        categorizations for accuracy.
      </div>
      <div class="section-head"><h2>Core Metrics</h2></div>
      <table>{core_table}</table>
      {industry_section}
    </div>
  </div>
</body>
</html>"""


def render_markdown(payload):
    if _is_multi_month(payload):
        return render_markdown_multi(payload)
    source = payload.get("source", "manual")
    business_type = payload.get("business_type", "other")
    industry_name = INDUSTRY_DISPLAY_NAMES.get(business_type, business_type.title())
    rows = _build_rows(payload.get("metrics", {}))
    industry_rows = _build_industry_rows(payload.get("industry_metrics", {}))

    lines = []
    lines.append("# Financial Report")
    lines.append("")
    lines.append(f"- Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"- Source: {source}")
    lines.append(f"- Industry: {industry_name}")
    lines.append("")
    lines.append(AI_DISCLAIMER)
    lines.append("")

    # Common metrics table
    lines.append("## Core Metrics")
    lines.append("")
    lines.append("| Metric | Value | Label | Reason | Missing Inputs |")
    lines.append("|---|---:|---|---|---|")
    for row in rows:
        lines.append(
            f"| {row['metric_name']} | {row['value']} | {row['label']} | {row['reason']} | {row['missing']} |"
        )
    lines.append("")

    # Industry-specific metrics table
    if industry_rows:
        lines.append(f"## {industry_name} Industry Metrics")
        lines.append("")
        lines.append("| Metric | Value | Label | Reason | Missing Inputs |")
        lines.append("|---|---:|---|---|---|")
        for row in industry_rows:
            lines.append(
                f"| {row['metric_name']} | {row['value']} | {row['label']} | {row['reason']} | {row['missing']} |"
            )
        lines.append("")

    return "\n".join(lines)


def render_html(payload):
    if _is_multi_month(payload):
        return render_html_multi(payload)
    source = escape(str(payload.get("source", "manual")))
    business_type = payload.get("business_type", "other")
    industry_name = escape(INDUSTRY_DISPLAY_NAMES.get(business_type, business_type.title()))
    rows = _build_rows(payload.get("metrics", {}))
    industry_rows = _build_industry_rows(payload.get("industry_metrics", {}))

    def _rows_to_html(row_list):
        html_parts = []
        for row in row_list:
            label = escape(row["label"])
            cls = f"label {label}" if label else "label"
            html_parts.append(
                "<tr>"
                f"<td>{escape(row['metric_name'])}</td>"
                f"<td class='num'>{escape(row['value'])}</td>"
                f"<td><span class='{cls}'>{label}</span></td>"
                f"<td>{escape(row['reason'])}</td>"
                f"<td>{escape(row['missing'])}</td>"
                "</tr>"
            )
        return "".join(html_parts)

    row_html = _rows_to_html(rows)
    industry_html = _rows_to_html(industry_rows)

    industry_section = ""
    if industry_rows:
        industry_section = f"""
      <div class="section-head"><h2>{industry_name} Industry Metrics</h2></div>
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            <th style="text-align:right">Value</th>
            <th>Label</th>
            <th>Reason</th>
            <th>Missing Inputs</th>
          </tr>
        </thead>
        <tbody>
          {industry_html}
        </tbody>
      </table>"""

    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Financial Report</title>
  <style>
    :root {{
      --bg: #0b1220;
      --panel: #111a2b;
      --panel-2: #0f1726;
      --text: #e5edf8;
      --muted: #9fb1c9;
      --line: #243247;
      --strong: #2dd4bf;
      --adequate: #60a5fa;
      --weak: #f59e0b;
      --critical: #ef4444;
      --insufficient_data: #a3a3a3;
      --not_applicable: #a3a3a3;
      --accent: #818cf8;
    }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    .wrap {{
      max-width: 1100px;
      margin: 24px auto;
      padding: 0 16px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 14px 36px rgba(0, 0, 0, 0.45);
      margin-bottom: 20px;
    }}
    .head {{
      padding: 16px;
      border-bottom: 1px solid var(--line);
    }}
    .section-head {{
      padding: 12px 16px;
      border-bottom: 1px solid var(--line);
      background: var(--panel-2);
    }}
    .section-head h2 {{
      margin: 0;
      font-size: 16px;
      color: var(--accent);
    }}
    h1 {{
      margin: 0 0 4px;
      font-size: 24px;
    }}
    .meta {{
      color: var(--muted);
      font-size: 13px;
    }}
    .disclaimer {{
      padding: 12px 16px;
      background: rgba(245, 158, 11, 0.08);
      border-left: 3px solid var(--weak);
      font-size: 12px;
      color: var(--muted);
      line-height: 1.5;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 13px;
    }}
    th {{
      background: var(--panel-2);
      font-weight: 600;
    }}
    td.num {{
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    .label {{
      display: inline-block;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 12px;
      border: 1px solid currentColor;
      line-height: 1.4;
    }}
    .strong {{ color: var(--strong); }}
    .adequate {{ color: var(--adequate); }}
    .weak {{ color: var(--weak); }}
    .critical {{ color: var(--critical); }}
    .insufficient_data {{ color: var(--insufficient_data); }}
    .not_applicable {{ color: var(--not_applicable); }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      <div class="head">
        <h1>Financial Report</h1>
        <div class="meta">Generated: {escape(generated)} | Source: {source} | Industry: {industry_name}</div>
      </div>
      <div class="disclaimer">
        ⚠️ <strong>AI Categorization Notice:</strong> Some metrics may have been derived from
        AI-categorized bank transactions. Only explicitly identified line items were summed —
        no percentage-based estimates or hardcoded assumptions were used. Please review
        categorizations for accuracy.
      </div>
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            <th style="text-align:right">Value</th>
            <th>Label</th>
            <th>Reason</th>
            <th>Missing Inputs</th>
          </tr>
        </thead>
        <tbody>
          {row_html}
        </tbody>
      </table>
      {industry_section}
    </div>
  </div>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="metrics_data.json")
    parser.add_argument("--md-out", default="financial_report.md")
    parser.add_argument("--html-out", default="financial_report.html")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    Path(args.md_out).write_text(render_markdown(payload), encoding="utf-8")
    Path(args.html_out).write_text(render_html(payload), encoding="utf-8")
    print(json.dumps({"md": args.md_out, "html": args.html_out}, indent=2))


if __name__ == "__main__":
    main()
