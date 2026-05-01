"""
General Financial Analyst metric engine.
Reads JSON from stdin and returns metric + insufficiency diagnostics as JSON.
"""
import csv
import json
import re
import sys


def _to_number(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", text)
    if cleaned in ("", "-", ".", "-."):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_bank_csv(csv_text):
    """
    Reusable lightweight parser for bank-style CSVs.
    Returns normalized monthly totals that can feed common metrics.
    """
    reader = csv.DictReader(csv_text.splitlines())
    inflow = 0.0
    outflow = 0.0
    ending_balance = None
    row_count = 0
    for row in reader:
        row_count += 1
        lower = {str(k).strip().lower(): v for k, v in row.items()}
        credit = _to_number(
            lower.get("deposit (credit)")
            or lower.get("credit")
            or lower.get("inflow")
        )
        debit = _to_number(
            lower.get("withdrawal (debit)")
            or lower.get("debit")
            or lower.get("outflow")
        )
        amount = _to_number(lower.get("amount"))
        balance = _to_number(lower.get("balance"))
        if credit is not None:
            inflow += credit
        if debit is not None:
            outflow += debit
        if amount is not None and credit is None and debit is None:
            if amount >= 0:
                inflow += amount
            else:
                outflow += abs(amount)
        if balance is not None:
            ending_balance = balance
    return {
        "source": "bank_csv",
        "rows": row_count,
        "monthly_revenue": round(inflow, 4),
        "monthly_opex": round(outflow, 4),
        "current_cash": round(ending_balance, 4) if ending_balance is not None else None,
    }


def verdict(metric_name, value):
    if value is None:
        return ("insufficient_data", "Cannot be determined from the provided inputs.")
    inf = float("inf")
    rules = {
        "runway": [
            (18, inf, "strong", ">= 18 months"),
            (12, 18, "adequate", "12-18 months"),
            (6, 12, "weak", "< 12 months"),
            (0, 6, "critical", "< 6 months"),
        ],
        "gross_margin_pct": [
            (75, inf, "strong", ">= 75%"),
            (60, 75, "adequate", "60-75%"),
            (0, 60, "weak", "< 60%"),
        ],
        "ltv_cac": [
            (5, inf, "strong", ">= 5x"),
            (3, 5, "strong", "3x-5x"),
            (1, 3, "adequate", "1x-3x"),
            (0, 1, "weak", "< 1x"),
        ],
        "churn_rate": [
            (0, 2, "strong", "< 2% monthly"),
            (2, 5, "adequate", "2-5% monthly"),
            (5, inf, "weak", "> 5% monthly"),
        ],
        "burn_multiple": [
            (0, 1, "strong", "< 1x"),
            (1, 1.5, "strong", "1x-1.5x"),
            (1.5, 2, "adequate", "1.5x-2x"),
            (2, 3, "weak", "2x-3x"),
            (3, inf, "critical", "> 3x"),
        ],
        "nrr": [
            (120, inf, "strong", ">= 120%"),
            (110, 120, "strong", "110-120%"),
            (100, 110, "adequate", "100-110%"),
            (0, 100, "weak", "< 100%"),
        ],
        "rule_of_40": [
            (40, inf, "strong", ">= 40"),
            (20, 40, "adequate", "20-40"),
            (-inf, 20, "weak", "< 20"),
        ],
        "cac_payback": [
            (0, 12, "strong", "< 12 months"),
            (12, 18, "adequate", "12-18 months"),
            (18, inf, "weak", "> 18 months"),
        ],
        "growth_rate": [
            (15, inf, "strong", ">= 15%"),
            (5, 15, "adequate", "5-15%"),
            (-inf, 5, "weak", "< 5%"),
        ],
    }
    for lo, hi, label, reason in rules.get(metric_name, []):
        if lo <= value < hi:
            return (label, reason)
    return ("adequate", "No benchmark configured for this metric.")


def _safe_round(value):
    if value is None:
        return None
    return round(value, 4)


def _metric(name, value, missing_inputs, benchmark_name=None):
    if missing_inputs:
        return {
            "value": None,
            "label": "insufficient_data",
            "reason": "Cannot be determined from the provided inputs.",
            "missing_inputs": missing_inputs,
        }
    label, reason = verdict(benchmark_name or name, value)
    return {
        "value": _safe_round(value),
        "label": label,
        "reason": reason,
        "missing_inputs": [],
    }


def _required(inputs, names):
    missing = []
    values = {}
    for name in names:
        val = inputs.get(name)
        if val is None:
            missing.append(name)
        else:
            num = _to_number(val)
            if num is None:
                missing.append(name)
            else:
                values[name] = num
    return missing, values


def compute_all(raw_inputs):
    inputs = dict(raw_inputs)
    if "bank_csv" in inputs and isinstance(inputs["bank_csv"], str):
        inputs.update(normalize_bank_csv(inputs["bank_csv"]))

    metrics = {}

    missing, v = _required(inputs, ["monthly_opex", "monthly_revenue"])
    net_burn = None if missing else v["monthly_opex"] - v["monthly_revenue"]
    metrics["1_net_burn"] = _metric("net_burn", net_burn, missing)

    missing, v = _required(inputs, ["current_cash"])
    runway_missing = list(missing)
    if net_burn is None:
        runway_missing.append("monthly_opex/monthly_revenue (for net_burn)")
        runway = None
    elif net_burn <= 0:
        runway = None
        runway_missing.append("positive_net_burn")
    else:
        runway = v["current_cash"] / net_burn
    metrics["2_runway"] = _metric("runway", runway, runway_missing, "runway")

    missing, v = _required(inputs, ["monthly_revenue", "cogs"])
    gm = (
        None
        if missing or v["monthly_revenue"] <= 0
        else (v["monthly_revenue"] - v["cogs"]) / v["monthly_revenue"] * 100
    )
    if not missing and v["monthly_revenue"] <= 0:
        missing = ["monthly_revenue must be > 0"]
    metrics["3_gross_margin"] = _metric("gross_margin_pct", gm, missing, "gross_margin_pct")

    missing, v = _required(inputs, ["sales_marketing_spend", "new_customers"])
    cac = None if missing or v["new_customers"] <= 0 else v["sales_marketing_spend"] / v["new_customers"]
    if not missing and v["new_customers"] <= 0:
        missing = ["new_customers must be > 0"]
    metrics["4_cac"] = _metric("cac", cac, missing)

    missing, v = _required(
        inputs, ["monthly_revenue", "active_customers", "lost_customers", "cogs"]
    )
    ltv = None
    if not missing:
        if v["active_customers"] <= 0:
            missing = ["active_customers must be > 0"]
        elif v["lost_customers"] <= 0:
            missing = ["lost_customers must be > 0 for finite LTV"]
        elif v["monthly_revenue"] <= 0:
            missing = ["monthly_revenue must be > 0"]
        else:
            arpu = v["monthly_revenue"] / v["active_customers"]
            gm_local = (v["monthly_revenue"] - v["cogs"]) / v["monthly_revenue"]
            churn = v["lost_customers"] / v["active_customers"]
            if churn <= 0:
                missing = ["churn_rate must be > 0 for finite LTV"]
            else:
                ltv = (arpu * gm_local) / churn
    metrics["5_ltv"] = _metric("ltv", ltv, missing)

    ltv_cac_missing = []
    if metrics["5_ltv"]["label"] == "insufficient_data":
        ltv_cac_missing.append("ltv")
    if metrics["4_cac"]["label"] == "insufficient_data":
        ltv_cac_missing.append("cac")
    ltv_cac = None if ltv_cac_missing else metrics["5_ltv"]["value"] / metrics["4_cac"]["value"]
    metrics["6_ltv_cac"] = _metric("ltv_cac", ltv_cac, ltv_cac_missing, "ltv_cac")

    missing, v = _required(inputs, ["monthly_revenue", "prev_monthly_revenue"])
    growth = (
        None
        if missing or v["prev_monthly_revenue"] <= 0
        else ((v["monthly_revenue"] - v["prev_monthly_revenue"]) / v["prev_monthly_revenue"]) * 100
    )
    if not missing and v["prev_monthly_revenue"] <= 0:
        missing = ["prev_monthly_revenue must be > 0"]
    metrics["7_revenue_growth"] = _metric("growth_rate", growth, missing, "growth_rate")

    missing, v = _required(inputs, ["lost_customers", "active_customers"])
    churn_logo = None if missing or v["active_customers"] <= 0 else (v["lost_customers"] / v["active_customers"]) * 100
    if not missing and v["active_customers"] <= 0:
        missing = ["active_customers must be > 0"]
    metrics["8_churn_logo"] = _metric("churn_rate", churn_logo, missing, "churn_rate")

    missing, v = _required(inputs, ["churned_mrr", "starting_mrr"])
    churn_rev = None if missing or v["starting_mrr"] <= 0 else (v["churned_mrr"] / v["starting_mrr"]) * 100
    if not missing and v["starting_mrr"] <= 0:
        missing = ["starting_mrr must be > 0"]
    metrics["8_churn_revenue"] = _metric("churn_rate", churn_rev, missing, "churn_rate")

    missing, v = _required(inputs, ["arr_end", "arr_start"])
    bm_missing = list(missing)
    if net_burn is None:
        bm_missing.append("monthly_opex/monthly_revenue (for net_burn)")
    burn_multiple = None
    if not bm_missing:
        net_new_arr = v["arr_end"] - v["arr_start"]
        if net_new_arr <= 0:
            bm_missing = ["arr_end must be > arr_start"]
        else:
            burn_multiple = net_burn / net_new_arr
    metrics["9_burn_multiple"] = _metric("burn_multiple", burn_multiple, bm_missing, "burn_multiple")

    missing, v = _required(inputs, ["starting_mrr", "expansion_mrr", "churned_mrr", "contraction_mrr"])
    nrr = (
        None
        if missing or v["starting_mrr"] <= 0
        else (
            (v["starting_mrr"] + v["expansion_mrr"] - v["churned_mrr"] - v["contraction_mrr"])
            / v["starting_mrr"]
        )
        * 100
    )
    if not missing and v["starting_mrr"] <= 0:
        missing = ["starting_mrr must be > 0"]
    metrics["10_nrr"] = _metric("nrr", nrr, missing, "nrr")

    missing, v = _required(inputs, ["revenue_growth_yoy_pct", "operating_margin_pct"])
    ro40 = None if missing else v["revenue_growth_yoy_pct"] + v["operating_margin_pct"]
    metrics["11_rule_of_40"] = _metric("rule_of_40", ro40, missing, "rule_of_40")

    payback_missing = []
    if metrics["4_cac"]["label"] == "insufficient_data":
        payback_missing.append("cac")
    gm_m = metrics["3_gross_margin"]["value"]
    missing2, v2 = _required(inputs, ["monthly_revenue", "active_customers"])
    payback_missing.extend(missing2)
    payback = None
    if not payback_missing:
        if v2["active_customers"] <= 0:
            payback_missing = ["active_customers must be > 0"]
        elif gm_m is None or gm_m <= 0:
            payback_missing = ["gross_margin must be > 0"]
        else:
            arpu = v2["monthly_revenue"] / v2["active_customers"]
            monthly_gross_profit = arpu * (gm_m / 100.0)
            if monthly_gross_profit <= 0:
                payback_missing = ["monthly_gross_profit must be > 0"]
            else:
                payback = metrics["4_cac"]["value"] / monthly_gross_profit
    metrics["12_cac_payback"] = _metric("cac_payback", payback, payback_missing, "cac_payback")

    return {
        "source": inputs.get("source", "manual"),
        "normalized_inputs_used": {k: v for k, v in inputs.items() if k != "bank_csv"},
        "metrics": metrics,
    }


if __name__ == "__main__":
    raw = sys.stdin.read().strip()
    payload = json.loads(raw) if raw else {}
    result = compute_all(payload)
    print(json.dumps(result, indent=2))
