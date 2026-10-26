#!/usr/bin/env python3
"""
Legacy Reference Pivot Implementation.
Simulates the old Excel workbook pivot logic using pandas independently.
Used for parity reconciliation testing.
"""

import os
import yaml
import pandas as pd
from typing import Dict, Any, Tuple

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "rules.yaml")

def load_rules(config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_reference_pivot(
    csv_path: str,
    rules_path: str = DEFAULT_CONFIG_PATH
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Applies the golden report filters and produces:
    1. Filtered deal dataframe with exact column subset
    2. Summary dictionary with grand total ACV, count, and UT30 grouping totals
    """
    rules = load_rules(rules_path)
    filters = rules.get("filters", {})
    output_cols = rules.get("output_columns", [
        "ut_level_30_dscr", "coverage_id", "signing_date",
        "sales_order_num", "customer_name", "saas_acv_usd_at_plan"
    ])

    df = pd.read_csv(csv_path, dtype={"sales_order_num": str, "coverage_id": str})
    
    # Cast ACV to float
    df["saas_acv_usd_at_plan"] = pd.to_numeric(df["saas_acv_usd_at_plan"], errors="coerce").fillna(0.0)

    # Apply filters
    mask = pd.Series(True, index=df.index)
    for col, val in filters.items():
        if col in df.columns:
            mask = mask & (df[col] == val)

    excluded_customers = rules.get("excluded_customers", [])
    if excluded_customers and "customer_name" in df.columns:
        mask = mask & (~df["customer_name"].isin(excluded_customers))

    filtered_df = df[mask].copy()

    # Calculate summary metrics
    subtotal_acv = float(filtered_df["saas_acv_usd_at_plan"].sum())
    subtotal_deals = int(len(filtered_df))

    manual_adjustments = rules.get("manual_adjustments", [])
    adj_acv = sum(float(a.get("acv_usd", 0.0)) for a in manual_adjustments)
    adj_deals = sum(int(a.get("deal_count", 0)) for a in manual_adjustments)

    total_acv = subtotal_acv + adj_acv
    deal_count = subtotal_deals + adj_deals
    avg_deal_size = total_acv / deal_count if deal_count > 0 else 0.0

    # Group by ut_level_30_dscr
    ut30_summary = (
        filtered_df.groupby("ut_level_30_dscr")["saas_acv_usd_at_plan"]
        .agg(["sum", "count"])
        .reset_index()
        .rename(columns={"sum": "total_acv", "count": "deal_count"})
        .to_dict(orient="records")
    )

    result_df = filtered_df[output_cols].copy()

    summary = {
        "grand_total_acv": round(total_acv, 2),
        "subtotal_acv": round(subtotal_acv, 2),
        "deal_count": deal_count,
        "subtotal_deal_count": subtotal_deals,
        "avg_deal_size": round(avg_deal_size, 2),
        "ut30_breakdown": ut30_summary
    }

    return result_df, summary

if __name__ == "__main__":
    import sys
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "data/snapshots/snapshot_2025-05-15.csv"
    if not os.path.exists(csv_file):
        csv_file = os.path.join(os.path.dirname(__file__), "..", csv_file)
        
    df, summary = run_reference_pivot(csv_file)
    print("=== Reference Excel Pivot Output ===")
    print(f"Total Rows: {summary['deal_count']}")
    print(f"Grand Total ACV: ${summary['grand_total_acv']:,.2f}")
    print(f"Average Deal Size: ${summary['avg_deal_size']:,.2f}")
    print("\nBreakdown by Product (UT30):")
    for row in summary["ut30_breakdown"]:
        print(f" - {row['ut_level_30_dscr']}: ${row['total_acv']:,.2f} ({row['deal_count']} deals)")
