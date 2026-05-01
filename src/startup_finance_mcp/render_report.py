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


def _fmt_value(value):
    if value is None:
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
                "value": _fmt_value(item.get("value")),
                "label": item.get("label", ""),
                "reason": item.get("reason", ""),
                "missing": ", ".join(item.get("missing_inputs", [])),
            }
        )
    return rows


def render_markdown(payload):
    source = payload.get("source", "manual")
    rows = _build_rows(payload.get("metrics", {}))
    lines = []
    lines.append("# Financial Report")
    lines.append("")
    lines.append(f"- Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"- Source: {source}")
    lines.append("")
    lines.append("| Metric | Value | Label | Reason | Missing Inputs |")
    lines.append("|---|---:|---|---|---|")
    for row in rows:
        lines.append(
            f"| {row['metric_name']} | {row['value']} | {row['label']} | {row['reason']} | {row['missing']} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_html(payload):
    source = escape(str(payload.get("source", "manual")))
    rows = _build_rows(payload.get("metrics", {}))
    row_html = []
    for row in rows:
        label = escape(row["label"])
        cls = f"label {label}" if label else "label"
        row_html.append(
            "<tr>"
            f"<td>{escape(row['metric_name'])}</td>"
            f"<td class='num'>{escape(row['value'])}</td>"
            f"<td><span class='{cls}'>{label}</span></td>"
            f"<td>{escape(row['reason'])}</td>"
            f"<td>{escape(row['missing'])}</td>"
            "</tr>"
        )

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
    }}
    .head {{
      padding: 16px;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{
      margin: 0 0 4px;
      font-size: 24px;
    }}
    .meta {{
      color: var(--muted);
      font-size: 13px;
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
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      <div class="head">
        <h1>Financial Report</h1>
        <div class="meta">Generated: {escape(generated)} | Source: {source}</div>
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
          {"".join(row_html)}
        </tbody>
      </table>
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
