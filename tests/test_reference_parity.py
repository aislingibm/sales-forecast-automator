import os
import pytest
from scripts.reference_pivot import run_reference_pivot
from scripts.generate_synthetic_data import create_snapshots

def test_forecast_engine_parity_with_reference_pivot(tmp_path):
    """
    Verify that the new Forecast Engine produces identical totals, deal counts,
    and product breakdowns to the legacy Reference Pivot script on synthetic data.
    """
    from app.engine.forecast import compute_forecast_from_df
    import pandas as pd

    out_dir = str(tmp_path / "snapshots")
    snapshots = create_snapshots(count=1000, seed=42, output_dir=out_dir)
    today_csv = snapshots["today"]

    # 1. Run reference pivot
    ref_df, ref_summary = run_reference_pivot(today_csv)

    # 2. Run new forecast engine
    raw_df = pd.read_csv(today_csv)
    engine_df, engine_summary = compute_forecast_from_df(raw_df)

    # Parity assertions: Exact to the penny
    assert engine_summary["grand_total_acv"] == ref_summary["grand_total_acv"]
    assert engine_summary["deal_count"] == ref_summary["deal_count"]
    assert engine_summary["avg_deal_size"] == ref_summary["avg_deal_size"]

    # Verify UT30 breakdown parity
    ref_breakdown = {item["ut_level_30_dscr"]: item["total_acv"] for item in ref_summary["ut30_breakdown"]}
    eng_breakdown = {item["ut_level_30_dscr"]: item["total_acv"] for item in engine_summary["ut30_breakdown"]}
    assert eng_breakdown == ref_breakdown
