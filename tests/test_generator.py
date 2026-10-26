import os
import pytest
import pandas as pd
from datetime import date, timedelta
from scripts.generate_synthetic_data import (
    generate_base_records,
    create_snapshots,
    get_as_of_date,
    DEFAULT_SEED
)

def test_signing_dates_fall_in_90_days_before_as_of(monkeypatch):
    """Signing dates must fall in the 90 days ending on the as-of date."""
    monkeypatch.setenv("AS_OF_DATE", "2026-10-26")
    assert get_as_of_date() == date(2026, 10, 26)

    records = generate_base_records(count=2000, seed=42)
    signing = [date.fromisoformat(r["signing_date"]) for r in records]
    assert max(signing) <= date(2026, 10, 26)
    assert min(signing) >= date(2026, 10, 26) - timedelta(days=89)

def test_same_seed_shifts_with_as_of_date():
    """Determinism: same seed, different as-of date => identical data except for the date shift."""
    a = generate_base_records(count=200, base_date=date(2026, 10, 26), seed=42)
    b = generate_base_records(count=200, base_date=date(2026, 10, 27), seed=42)
    for ra, rb in zip(a, b):
        assert date.fromisoformat(rb["signing_date"]) - date.fromisoformat(ra["signing_date"]) == timedelta(days=1)
        assert {k: v for k, v in ra.items() if k != "signing_date"} == {k: v for k, v in rb.items() if k != "signing_date"}

def test_snapshot_files_named_with_as_of_date(tmp_path):
    out_dir = str(tmp_path / "snapshots")
    result = create_snapshots(count=300, seed=42, output_dir=out_dir, as_of=date(2026, 10, 26))
    assert os.path.basename(result["today"]) == "snapshot_2026-10-26.csv"
    assert os.path.basename(result["yesterday"]) == "snapshot_2026-10-25.csv"

    df = pd.read_csv(result["today"])
    assert df["signing_date"].min() >= "2026-07-29"  # 90-day window start
    assert df["signing_date"].max() <= "2026-10-26"

def test_generator_determinism():
    """Verify that same seed generates identical records."""
    rec1 = generate_base_records(count=100, seed=42)
    rec2 = generate_base_records(count=100, seed=42)
    rec3 = generate_base_records(count=100, seed=99)

    assert rec1 == rec2
    assert rec1 != rec3

def test_generator_synthetic_compliance():
    """Verify that NO real customer names or unapproved domains exist."""
    records = generate_base_records(count=500, seed=42)
    for r in records:
        assert r["customer_name"].startswith("Acme Test Enterprise ")
        assert float(r["saas_acv_usd_at_plan"]) > 0
        assert r["country"] in ["United States", "Canada", "United Kingdom", "Germany", "Japan"]

def test_snapshot_creation(tmp_path):
    """Verify snapshot CSV generation and injected anomalies."""
    out_dir = str(tmp_path / "snapshots")
    result = create_snapshots(count=500, seed=DEFAULT_SEED, output_dir=out_dir)

    assert os.path.exists(result["yesterday"])
    assert os.path.exists(result["today"])
    
    anomalies = result["anomalies"]
    assert len(anomalies["duplicates"]) == 5
    assert len(anomalies["missing_coverage_ids"]) == 10
    assert len(anomalies["invalid_acv"]) == 6
