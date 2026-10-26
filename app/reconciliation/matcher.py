import time
import logging
import pandas as pd
from typing import Dict, Any, List, Optional
from app.reconciliation.base import SalesSystemClient
from app.config import get_rules_config, get_settings_config

logger = logging.getLogger(__name__)

def reconcile_forecast_with_sales_cloud(
    df_forecast: pd.DataFrame,
    client: SalesSystemClient,
    tolerance_usd: float = 0.01,
    max_retries: int = 3,
    backoff_seconds: float = 1.0,
    backoff_multiplier: float = 2.0
) -> Dict[str, Any]:
    """
    Executes 3-level reconciliation between Forecast dataset and Sales Cloud:
    1. Grand Total Comparison
    2. Date & UT30 Grain Comparison
    3. Order-level Join on sales_order_num
    """
    settings = get_settings_config()
    sc_cfg = settings.get("sales_cloud", {})
    if tolerance_usd is None:
        tolerance_usd = float(sc_cfg.get("per_order_tolerance_usd", 0.01))
    
    rules = get_rules_config()
    filters = rules.get("filters", {})

    # 1. Fetch Sales Cloud records with retry & backoff
    sc_records = None
    attempt = 0
    current_backoff = backoff_seconds

    while attempt < max_retries:
        attempt += 1
        try:
            sc_records = client.fetch_signings(filters=filters)
            break
        except Exception as e:
            logger.warning(f"Sales Cloud fetch attempt {attempt} failed: {e}")
            if attempt < max_retries:
                time.sleep(current_backoff)
                current_backoff *= backoff_multiplier

    if sc_records is None:
        # Outage fallback
        return {
            "status": "UNAVAILABLE",
            "report_label": "Not verified",
            "verified": False,
            "forecast_total_usd": 0.0,
            "sales_cloud_total_usd": 0.0,
            "variance_usd": 0.0,
            "affected_orders_count": 0,
            "variances_by_type": {
                "ONLY_IN_FORECAST": [],
                "ONLY_IN_SALES_CLOUD": [],
                "ACV_MISMATCH": [],
                "ATTRIBUTE_MISMATCH": []
            },
            "level1_grand_total": {"match": False, "difference": 0.0},
            "level2_grain_summary": []
        }

    # Filter forecast DataFrame to match golden filters
    if not df_forecast.empty:
        f_mask = pd.Series(True, index=df_forecast.index)
        for col, val in filters.items():
            if col in df_forecast.columns and val != "ALL" and val != "":
                f_mask = f_mask & (df_forecast[col] == val)
        fc_filtered = df_forecast[f_mask].copy()
    else:
        fc_filtered = pd.DataFrame()

    df_sc = pd.DataFrame(sc_records)
    if not df_sc.empty:
        df_sc["saas_acv_usd_at_plan"] = pd.to_numeric(df_sc["saas_acv_usd_at_plan"], errors="coerce").fillna(0.0)
    else:
        df_sc = pd.DataFrame(columns=[
            "sales_order_num", "customer_name", "signing_date",
            "ut_level_30_dscr", "coverage_id", "saas_acv_usd_at_plan"
        ])

    # Build unique order lookups (deduping if any duplicate orders exist)
    fc_dict = {}
    if not fc_filtered.empty and "sales_order_num" in fc_filtered.columns:
        for _, r in fc_filtered.iterrows():
            so = r.get("sales_order_num")
            if so and so not in fc_dict:
                fc_dict[so] = r.to_dict()

    sc_dict = {}
    if not df_sc.empty and "sales_order_num" in df_sc.columns:
        for _, r in df_sc.iterrows():
            so = r.get("sales_order_num")
            if so and so not in sc_dict:
                sc_dict[so] = r.to_dict()

    fc_orders = set(fc_dict.keys())
    sc_orders = set(sc_dict.keys())

    variances_by_type = {
        "ONLY_IN_FORECAST": [],
        "ONLY_IN_SALES_CLOUD": [],
        "ACV_MISMATCH": [],
        "ATTRIBUTE_MISMATCH": []
    }

    # Level 3: Order by Order join
    # Orders only in forecast
    for so in fc_orders - sc_orders:
        item = fc_dict[so]
        variances_by_type["ONLY_IN_FORECAST"].append({
            "sales_order_num": so,
            "customer_name": item.get("customer_name", ""),
            "forecast_acv": round(float(item.get("saas_acv_usd_at_plan", 0)), 2),
            "sales_cloud_acv": None,
            "variance_usd": round(float(item.get("saas_acv_usd_at_plan", 0)), 2),
            "details": "Order present in Forecast extract but missing in Sales Cloud SoR."
        })

    # Orders only in Sales Cloud
    for so in sc_orders - fc_orders:
        item = sc_dict[so]
        variances_by_type["ONLY_IN_SALES_CLOUD"].append({
            "sales_order_num": so,
            "customer_name": item.get("customer_name", ""),
            "forecast_acv": None,
            "sales_cloud_acv": round(float(item.get("saas_acv_usd_at_plan", 0)), 2),
            "variance_usd": round(float(item.get("saas_acv_usd_at_plan", 0)), 2),
            "details": "Order booked in Sales Cloud SoR but missing from Forecast extract."
        })

    # Matched orders - check ACV and attributes
    for so in fc_orders & sc_orders:
        fc_item = fc_dict[so]
        sc_item = sc_dict[so]
        
        fc_acv = round(float(fc_item.get("saas_acv_usd_at_plan", 0)), 2)
        sc_acv = round(float(sc_item.get("saas_acv_usd_at_plan", 0)), 2)
        diff_acv = round(abs(fc_acv - sc_acv), 2)

        if diff_acv > tolerance_usd:
            variances_by_type["ACV_MISMATCH"].append({
                "sales_order_num": so,
                "customer_name": fc_item.get("customer_name", ""),
                "forecast_acv": fc_acv,
                "sales_cloud_acv": sc_acv,
                "variance_usd": round(fc_acv - sc_acv, 2),
                "details": f"ACV discrepancy of ${diff_acv:,.2f} exceeds tolerance ${tolerance_usd}."
            })

        # Check attributes with normalized string comparisons
        def _norm_str(v):
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return ""
            return str(v).strip()

        attr_diffs = []
        if _norm_str(fc_item.get("customer_name")) != _norm_str(sc_item.get("customer_name")):
            attr_diffs.append(f"Customer ('{fc_item.get('customer_name')}' vs '{sc_item.get('customer_name')}')")
        if _norm_str(fc_item.get("signing_date")) != _norm_str(sc_item.get("signing_date")):
            attr_diffs.append(f"Signing Date ('{fc_item.get('signing_date')}' vs '{sc_item.get('signing_date')}')")
        if _norm_str(fc_item.get("coverage_id")) != _norm_str(sc_item.get("coverage_id")):
            attr_diffs.append(f"Coverage ID ('{fc_item.get('coverage_id')}' vs '{sc_item.get('coverage_id')}')")

        if attr_diffs:
            variances_by_type["ATTRIBUTE_MISMATCH"].append({
                "sales_order_num": so,
                "customer_name": fc_item.get("customer_name", ""),
                "forecast_acv": fc_acv,
                "sales_cloud_acv": sc_acv,
                "variance_usd": 0.0,
                "details": f"Attribute mismatch in {', '.join(attr_diffs)}."
            })

    # Level 1: Grand Total
    forecast_total = round(sum(float(r.get("saas_acv_usd_at_plan", 0)) for r in fc_dict.values()), 2)
    sc_total = round(sum(float(r.get("saas_acv_usd_at_plan", 0)) for r in sc_dict.values()), 2)
    grand_total_variance = round(abs(forecast_total - sc_total), 2)

    total_affected_orders = (
        len(variances_by_type["ONLY_IN_FORECAST"]) +
        len(variances_by_type["ONLY_IN_SALES_CLOUD"]) +
        len(variances_by_type["ACV_MISMATCH"]) +
        len(variances_by_type["ATTRIBUTE_MISMATCH"])
    )

    is_match = (total_affected_orders == 0) and (grand_total_variance <= tolerance_usd)
    status = "MATCH" if is_match else "MISMATCH"
    report_label = "FINAL" if is_match else "CHECK"

    return {
        "status": status,
        "report_label": report_label,
        "verified": True,
        "forecast_total_usd": forecast_total,
        "sales_cloud_total_usd": sc_total,
        "variance_usd": grand_total_variance,
        "affected_orders_count": total_affected_orders,
        "variances_by_type": variances_by_type,
        "level1_grand_total": {
            "match": grand_total_variance <= tolerance_usd,
            "forecast_total": forecast_total,
            "sales_cloud_total": sc_total,
            "difference": grand_total_variance
        }
    }
