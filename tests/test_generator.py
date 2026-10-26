import os
import pytest
from scripts.generate_synthetic_data import (
    generate_base_records,
    create_snapshots,
    DEFAULT_SEED
)

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
