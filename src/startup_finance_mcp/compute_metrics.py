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
        # Industry-specific benchmarks
        "ecom_ad_spend_ratio": [
            (0, 15, "strong", "< 15% of revenue"),
            (15, 30, "adequate", "15-30% of revenue"),
            (30, inf, "weak", "> 30% of revenue"),
        ],
        "ecom_refund_rate": [
            (0, 2, "strong", "< 2%"),
            (2, 5, "adequate", "2-5%"),
            (5, inf, "weak", "> 5%"),
        ],
        "svc_payroll_ratio": [
            (0, 50, "strong", "< 50% of revenue"),
            (50, 70, "adequate", "50-70% of revenue"),
            (70, inf, "weak", "> 70% of revenue"),
        ],
        "svc_client_concentration": [
            (0, 25, "strong", "< 25% from top client"),
            (25, 50, "adequate", "25-50% from top client"),
            (50, inf, "weak", "> 50% from top client"),
        ],
        "fp_expense_ratio": [
            (0, 50, "strong", "< 50% of revenue"),
            (50, 75, "adequate", "50-75% of revenue"),
            (75, inf, "weak", "> 75% of revenue"),
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
        metrics["2_runway"] = _metric("runway", runway, runway_missing, "runway")
    elif net_burn <= 0:
        metrics["2_runway"] = {
            "value": None,
            "label": "not_applicable",
            "reason": "Business is cash flow positive",
            "missing_inputs": [],
        }
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
    if not bm_missing and net_burn is not None and net_burn <= 0:
        metrics["9_burn_multiple"] = {
            "value": None,
            "label": "not_applicable",
            "reason": "Business is cash flow positive",
            "missing_inputs": [],
        }
    else:
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

    # ── Industry-specific metrics ──────────────────────────────────────────
    business_type = str(inputs.get("business_type", "other")).lower().strip()
    industry_metrics = {}

    if business_type == "saas":
        mr_val = _to_number(inputs.get("monthly_revenue"))
        if mr_val is not None:
            industry_metrics["ind_mrr"] = _metric("ind_mrr", mr_val, [])
            industry_metrics["ind_arr"] = _metric("ind_arr", mr_val * 12, [])
        else:
            industry_metrics["ind_mrr"] = _metric("ind_mrr", None, ["monthly_revenue"])
            industry_metrics["ind_arr"] = _metric("ind_arr", None, ["monthly_revenue"])

    elif business_type == "ecommerce":
        # AOV
        missing_aov, v_aov = _required(inputs, ["monthly_revenue", "total_orders"])
        aov = None
        if not missing_aov:
            if v_aov["total_orders"] <= 0:
                missing_aov = ["total_orders must be > 0"]
            else:
                aov = v_aov["monthly_revenue"] / v_aov["total_orders"]
        industry_metrics["ind_aov"] = _metric("ind_aov", aov, missing_aov)

        # Ad Spend Ratio
        missing_ad, v_ad = _required(inputs, ["sales_marketing_spend", "monthly_revenue"])
        ad_ratio = None
        if not missing_ad:
            if v_ad["monthly_revenue"] <= 0:
                missing_ad = ["monthly_revenue must be > 0"]
            else:
                ad_ratio = (v_ad["sales_marketing_spend"] / v_ad["monthly_revenue"]) * 100
        industry_metrics["ind_ad_spend_ratio"] = _metric(
            "ecom_ad_spend_ratio", ad_ratio, missing_ad, "ecom_ad_spend_ratio"
        )

        # Refund Rate
        missing_ref, v_ref = _required(inputs, ["refund_amount", "monthly_revenue"])
        refund_rate = None
        if not missing_ref:
            if v_ref["monthly_revenue"] <= 0:
                missing_ref = ["monthly_revenue must be > 0"]
            else:
                refund_rate = (v_ref["refund_amount"] / v_ref["monthly_revenue"]) * 100
        industry_metrics["ind_refund_rate"] = _metric(
            "ecom_refund_rate", refund_rate, missing_ref, "ecom_refund_rate"
        )

    elif business_type == "services":
        # Revenue per client
        missing_rpc, v_rpc = _required(inputs, ["monthly_revenue", "active_customers"])
        rpc = None
        if not missing_rpc:
            if v_rpc["active_customers"] <= 0:
                missing_rpc = ["active_customers must be > 0"]
            else:
                rpc = v_rpc["monthly_revenue"] / v_rpc["active_customers"]
        industry_metrics["ind_revenue_per_client"] = _metric("ind_revenue_per_client", rpc, missing_rpc)

        # Payroll ratio
        missing_pr, v_pr = _required(inputs, ["payroll_spend", "monthly_revenue"])
        pr = None
        if not missing_pr:
            if v_pr["monthly_revenue"] <= 0:
                missing_pr = ["monthly_revenue must be > 0"]
            else:
                pr = (v_pr["payroll_spend"] / v_pr["monthly_revenue"]) * 100
        industry_metrics["ind_payroll_ratio"] = _metric(
            "svc_payroll_ratio", pr, missing_pr, "svc_payroll_ratio"
        )

        # Client concentration
        missing_cc, v_cc = _required(inputs, ["top_client_revenue", "monthly_revenue"])
        cc = None
        if not missing_cc:
            if v_cc["monthly_revenue"] <= 0:
                missing_cc = ["monthly_revenue must be > 0"]
            else:
                cc = (v_cc["top_client_revenue"] / v_cc["monthly_revenue"]) * 100
        industry_metrics["ind_client_concentration"] = _metric(
            "svc_client_concentration", cc, missing_cc, "svc_client_concentration"
        )

    elif business_type in ("freelancer", "professional_practice"):
        # Expense ratio
        missing_er, v_er = _required(inputs, ["monthly_opex", "monthly_revenue"])
        er = None
        if not missing_er:
            if v_er["monthly_revenue"] <= 0:
                missing_er = ["monthly_revenue must be > 0"]
            else:
                er = (v_er["monthly_opex"] / v_er["monthly_revenue"]) * 100
        industry_metrics["ind_expense_ratio"] = _metric(
            "fp_expense_ratio", er, missing_er, "fp_expense_ratio"
        )

        # Effective hourly rate
        missing_ehr, v_ehr = _required(inputs, ["monthly_revenue", "billable_hours"])
        ehr = None
        if not missing_ehr:
            if v_ehr["billable_hours"] <= 0:
                missing_ehr = ["billable_hours must be > 0"]
            else:
                ehr = v_ehr["monthly_revenue"] / v_ehr["billable_hours"]
        industry_metrics["ind_effective_hourly_rate"] = _metric(
            "ind_effective_hourly_rate", ehr, missing_ehr
        )

    return {
        "source": inputs.get("source", "manual"),
        "business_type": business_type,
        "normalized_inputs_used": {k: v for k, v in inputs.items() if k != "bank_csv"},
        "metrics": metrics,
        "industry_metrics": industry_metrics,
    }


if __name__ == "__main__":
    raw = sys.stdin.read().strip()
    payload = json.loads(raw) if raw else {}
    result = compute_all(payload)
    print(json.dumps(result, indent=2))
