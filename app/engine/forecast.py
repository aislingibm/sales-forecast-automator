import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
import app.config

def compute_forecast_from_df(
    df: pd.DataFrame,
    custom_filters: Optional[Dict[str, Any]] = None,
    group_by: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Applies configurable filter rules and groups forecast data.
    Ensures mathematical parity with the legacy Excel pivot table.
    """
    if df.empty:
        return pd.DataFrame(), {
            "grand_total_acv": 0.0,
            "deal_count": 0,
            "avg_deal_size": 0.0,
            "ut30_breakdown": [],
            "grouped_data": []
        }

    rules = app.config.get_rules_config()
    base_filters = dict(rules.get("filters", {}))
    
    # Override with custom parameters if supplied
    if custom_filters:
        for k, v in custom_filters.items():
            if v is not None:
                base_filters[k] = v

    working_df = df.copy()
    working_df["saas_acv_usd_at_plan"] = pd.to_numeric(working_df["saas_acv_usd_at_plan"], errors="coerce").fillna(0.0)

    # Filter mask
    mask = pd.Series(True, index=working_df.index)
    for col, val in base_filters.items():
        if col in working_df.columns and val != "ALL" and val != "":
            mask = mask & (working_df[col] == val)

    # Honor excluded_customers rule
    excluded_customers = rules.get("excluded_customers", [])
    if excluded_customers and "customer_name" in working_df.columns:
        mask = mask & (~working_df["customer_name"].isin(excluded_customers))

    if date_from and "signing_date" in working_df.columns:
        mask = mask & (working_df["signing_date"] >= date_from)
    if date_to and "signing_date" in working_df.columns:
        mask = mask & (working_df["signing_date"] <= date_to)

    filtered_df = working_df[mask].copy()

    # Extract subtotal metrics
    subtotal_acv = float(filtered_df["saas_acv_usd_at_plan"].sum())
    subtotal_deals = int(len(filtered_df))

    # Honor manual adjustments rule
    manual_adjustments = rules.get("manual_adjustments", [])
    adj_acv = sum(float(a.get("acv_usd", 0.0)) for a in manual_adjustments)
    adj_deals = sum(int(a.get("deal_count", 0)) for a in manual_adjustments)

    total_acv = subtotal_acv + adj_acv
    deal_count = subtotal_deals + adj_deals
    avg_deal_size = total_acv / deal_count if deal_count > 0 else 0.0

    # UT30 summary
    ut30_summary = []
    if "ut_level_30_dscr" in filtered_df.columns and not filtered_df.empty:
        ut30_summary = (
            filtered_df.groupby("ut_level_30_dscr")["saas_acv_usd_at_plan"]
            .agg(["sum", "count"])
            .reset_index()
            .rename(columns={"sum": "total_acv", "count": "deal_count"})
            .sort_values(by="total_acv", ascending=False)
            .to_dict(orient="records")
        )
        for item in ut30_summary:
            item["total_acv"] = round(float(item["total_acv"]), 2)

    # Dynamic Grouping
    grouped_data = []
    if group_by and not filtered_df.empty:
        temp_df = filtered_df.copy()
        
        if group_by in ["day", "signing_date"]:
            grp_col = "signing_date"
        elif group_by in ["week"]:
            temp_df["week"] = pd.to_datetime(temp_df["signing_date"]).dt.to_period("W").astype(str)
            grp_col = "week"
        elif group_by in ["month"]:
            temp_df["month"] = pd.to_datetime(temp_df["signing_date"]).dt.to_period("M").astype(str)
            grp_col = "month"
        elif group_by in ["quarter"]:
            temp_df["quarter"] = pd.to_datetime(temp_df["signing_date"]).dt.to_period("Q").astype(str)
            grp_col = "quarter"
        elif group_by in ["ut_level_30", "ut_level_30_dscr"]:
            grp_col = "ut_level_30_dscr"
        elif group_by in ["customer", "customer_name"]:
            grp_col = "customer_name"
        else:
            grp_col = "signing_date"

        if grp_col in temp_df.columns:
            grouped_df = (
                temp_df.groupby(grp_col)["saas_acv_usd_at_plan"]
                .agg(["sum", "count"])
                .reset_index()
                .rename(columns={grp_col: "group_key", "sum": "total_acv", "count": "deal_count"})
                .sort_values(by="group_key")
            )
            for _, r in grouped_df.iterrows():
                grouped_data.append({
                    "group_key": str(r["group_key"]),
                    "total_acv": round(float(r["total_acv"]), 2),
                    "deal_count": int(r["deal_count"])
                })

    output_cols = rules.get("output_columns", [
        "ut_level_30_dscr", "coverage_id", "signing_date",
        "sales_order_num", "customer_name", "saas_acv_usd_at_plan"
    ])
    
    # Ensure all output columns exist
    for col in output_cols:
        if col not in filtered_df.columns:
            filtered_df[col] = ""

    result_df = filtered_df[output_cols].copy()

    summary = {
        "grand_total_acv": round(total_acv, 2),
        "subtotal_acv": round(subtotal_acv, 2),
        "deal_count": deal_count,
        "subtotal_deal_count": subtotal_deals,
        "avg_deal_size": round(avg_deal_size, 2),
        "manual_adjustments": manual_adjustments,
        "ut30_breakdown": ut30_summary,
        "grouped_data": grouped_data
    }

    return result_df, summary

def compute_day_over_day_changes(
    df_today: pd.DataFrame,
    df_yesterday: pd.DataFrame
) -> Dict[str, Any]:
    """
    Computes delta between two snapshots:
    - Added deals
    - Removed deals
    - ACV Modifications
    """
    if df_today.empty or df_yesterday.empty:
        return {
            "added_deals": [],
            "removed_deals": [],
            "modified_deals": [],
            "net_acv_change": 0.0,
            "pct_change": 0.0
        }

    # Dedup on sales_order_num for comparison
    today_map = {
        r["sales_order_num"]: r for _, r in df_today.iterrows()
        if r.get("sales_order_num")
    }
    yesterday_map = {
        r["sales_order_num"]: r for _, r in df_yesterday.iterrows()
        if r.get("sales_order_num")
    }

    today_orders = set(today_map.keys())
    yesterday_orders = set(yesterday_map.keys())

    added_keys = today_orders - yesterday_orders
    removed_keys = yesterday_orders - today_orders
    common_keys = today_orders & yesterday_orders

    added_deals = [
        {
            "sales_order_num": k,
            "customer_name": today_map[k].get("customer_name", ""),
            "ut_level_30_dscr": today_map[k].get("ut_level_30_dscr", ""),
            "acv": round(float(today_map[k].get("saas_acv_usd_at_plan", 0)), 2)
        }
        for k in added_keys
    ]

    removed_deals = [
        {
            "sales_order_num": k,
            "customer_name": yesterday_map[k].get("customer_name", ""),
            "ut_level_30_dscr": yesterday_map[k].get("ut_level_30_dscr", ""),
            "acv": round(float(yesterday_map[k].get("saas_acv_usd_at_plan", 0)), 2)
        }
        for k in removed_keys
    ]

    modified_deals = []
    for k in common_keys:
        acv_today = round(float(today_map[k].get("saas_acv_usd_at_plan", 0)), 2)
        acv_yest = round(float(yesterday_map[k].get("saas_acv_usd_at_plan", 0)), 2)
        delta = round(acv_today - acv_yest, 2)
        if abs(delta) > 0.01:
            modified_deals.append({
                "sales_order_num": k,
                "customer_name": today_map[k].get("customer_name", ""),
                "ut_level_30_dscr": today_map[k].get("ut_level_30_dscr", ""),
                "yesterday_acv": acv_yest,
                "today_acv": acv_today,
                "delta": delta
            })

    total_today = float(df_today["saas_acv_usd_at_plan"].sum())
    total_yest = float(df_yesterday["saas_acv_usd_at_plan"].sum())
    net_acv_change = round(total_today - total_yest, 2)
    pct_change = round((net_acv_change / total_yest) * 100, 2) if total_yest > 0 else 0.0

    return {
        "added_deals": added_deals,
        "removed_deals": removed_deals,
        "modified_deals": modified_deals,
        "net_acv_change": net_acv_change,
        "pct_change": pct_change
    }
