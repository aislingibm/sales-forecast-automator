import os
import pytest
import pandas as pd
from scripts.generate_synthetic_data import create_snapshots, get_as_of_date, DEFAULT_SEED
from app.quality.checker import run_quality_checks

def test_quality_checks_detect_all_planted_anomalies(tmp_path):
    """
    Verify that quality engine flags all 4 categories of data anomalies:
    1. Duplicate sales_order_num
    2. Missing coverage_id
    3. Negative/Zero ACV
    4. Day-over-Day ACV swing exceeding threshold
    """
    out_dir = str(tmp_path / "snapshots")
    snapshots = create_snapshots(count=1000, seed=DEFAULT_SEED, output_dir=out_dir)
    
    df_today = pd.read_csv(snapshots["today"])
    df_yesterday = pd.read_csv(snapshots["yesterday"])
    
    findings = run_quality_checks(
        df_today=df_today,
        df_yesterday=df_yesterday,
        swing_threshold_pct=25.0
    )

    # 1. Duplicates
    assert findings["duplicates_count"] == 5
    assert len(findings["duplicate_orders"]) == 5

    # 2. Missing Coverage ID
    assert findings["missing_coverage_id_count"] == 10

    # 3. Invalid ACV (4 negative + 2 zero = 6)
    assert findings["invalid_acv_count"] == 6

    # 4. Overall status
    assert findings["status"] == "WARNING"
    assert len(findings["issues"]) > 0

def test_quality_clean_dataset():
    """Verify that a clean dataset produces PASS status."""
    clean_data = [
        {
            "sales_order_num": f"SO-{i:05d}",
            "coverage_id": f"COV-{i:05d}",
            "saas_acv_usd_at_plan": 10000.0,
            "signing_date": get_as_of_date().isoformat(),
            "country": "United States",
            "client_sub_type": "Select T Activate",
            "signing_category": "New Signings",
            "ut_level_15_dscr": "Data Platform",
            "ut_level_30_dscr": "watsonx.data Core",
            "customer_name": f"Acme {i}"
        }
        for i in range(1, 20)
    ]
    df_clean = pd.DataFrame(clean_data)
    findings = run_quality_checks(df_today=df_clean, df_yesterday=df_clean)
    
    assert findings["status"] == "PASS"
    assert findings["duplicates_count"] == 0
    assert findings["missing_coverage_id_count"] == 0
    assert findings["invalid_acv_count"] == 0
