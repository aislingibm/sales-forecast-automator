import pandas as pd
from typing import Dict, Any, List, Optional
from app.config import get_rules_config

def run_quality_checks(
    df_today: pd.DataFrame,
    df_yesterday: Optional[pd.DataFrame] = None,
    swing_threshold_pct: Optional[float] = None
) -> Dict[str, Any]:
    """
    Executes automated data quality rules on the snapshot dataframe:
    1. Duplicate sales_order_num
    2. Missing coverage_id
    3. Negative or zero ACV
    4. Day-over-day total swing exceeding threshold (default 25%)
    """
    if swing_threshold_pct is None:
        rules = get_rules_config()
        swing_threshold_pct = float(rules.get("quality", {}).get("swing_threshold_pct", 25.0))

    issues = []
    
    # 1. Duplicate sales_order_num
    duplicate_orders = []
    if "sales_order_num" in df_today.columns:
        valid_orders = df_today[df_today["sales_order_num"].notnull() & (df_today["sales_order_num"] != "")]
        duplicates_mask = valid_orders.duplicated(subset=["sales_order_num"], keep=False)
        dup_df = valid_orders[duplicates_mask]
        duplicate_orders = sorted(list(dup_df["sales_order_num"].unique()))
        
        if duplicate_orders:
            issues.append(f"Found {len(duplicate_orders)} duplicate sales order numbers.")

    # 2. Missing coverage_id
    missing_cov_orders = []
    if "coverage_id" in df_today.columns:
        missing_cov_mask = df_today["coverage_id"].isna() | (df_today["coverage_id"] == "")
        missing_cov_df = df_today[missing_cov_mask]
        if "sales_order_num" in missing_cov_df.columns:
            missing_cov_orders = list(missing_cov_df["sales_order_num"].dropna())
        else:
            missing_cov_orders = ["<unknown>" for _ in range(len(missing_cov_df))]
            
        if len(missing_cov_df) > 0:
            issues.append(f"Found {len(missing_cov_df)} records with missing coverage ID.")

    # 3. Invalid ACV (<= 0)
    invalid_acv_records = []
    if "saas_acv_usd_at_plan" in df_today.columns:
        numeric_acv = pd.to_numeric(df_today["saas_acv_usd_at_plan"], errors="coerce").fillna(0.0)
        invalid_mask = numeric_acv <= 0
        invalid_df = df_today[invalid_mask]
        
        for _, row in invalid_df.iterrows():
            so = row.get("sales_order_num", "UNKNOWN")
            val = row.get("saas_acv_usd_at_plan", 0)
            invalid_acv_records.append({"sales_order_num": so, "acv": val})
            
        if len(invalid_df) > 0:
            issues.append(f"Found {len(invalid_df)} records with zero or negative ACV.")

    # 4. Day-over-Day Total Swing Check
    swing_flagged = False
    dod_swing_pct = 0.0
    if df_yesterday is not None and not df_yesterday.empty and not df_today.empty:
        total_today = float(pd.to_numeric(df_today["saas_acv_usd_at_plan"], errors="coerce").fillna(0.0).sum())
        total_yest = float(pd.to_numeric(df_yesterday["saas_acv_usd_at_plan"], errors="coerce").fillna(0.0).sum())
        
        if total_yest > 0:
            dod_swing_pct = abs((total_today - total_yest) / total_yest) * 100.0
            if dod_swing_pct > swing_threshold_pct:
                swing_flagged = True
                issues.append(
                    f"Day-over-day total ACV swing of {dod_swing_pct:.1f}% exceeds threshold of {swing_threshold_pct:.1f}%."
                )

    status = "WARNING" if (duplicate_orders or missing_cov_orders or invalid_acv_records or swing_flagged) else "PASS"

    return {
        "status": status,
        "duplicates_count": len(duplicate_orders),
        "duplicate_orders": duplicate_orders,
        "missing_coverage_id_count": len(missing_cov_orders),
        "missing_coverage_orders": missing_cov_orders,
        "invalid_acv_count": len(invalid_acv_records),
        "invalid_acv_records": invalid_acv_records,
        "dod_swing_pct": round(dod_swing_pct, 2),
        "swing_flagged": swing_flagged,
        "issues": issues
    }
