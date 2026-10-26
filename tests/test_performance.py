import time
import pytest
import pandas as pd
from scripts.generate_synthetic_data import generate_base_records
from app.engine.forecast import compute_forecast_from_df

def test_performance_50k_rows():
    """
    Non-functional requirement:
    The report responds in under 2 seconds for 50,000 rows.
    """
    # Generate 50k synthetic records
    records = generate_base_records(count=50000, seed=123)
    df_large = pd.DataFrame(records)

    start_time = time.perf_counter()
    filtered_df, summary = compute_forecast_from_df(df_large)
    elapsed_seconds = time.perf_counter() - start_time

    print(f"\n[Performance Test] Processed 50,000 rows in {elapsed_seconds:.4f} seconds.")
    assert elapsed_seconds < 2.0, f"Query took {elapsed_seconds:.2f}s, exceeding 2.0s limit."
    assert summary["deal_count"] > 0
    assert summary["grand_total_acv"] > 0
