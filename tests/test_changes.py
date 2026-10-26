import pytest
import pandas as pd
from scripts.generate_synthetic_data import create_snapshots, DEFAULT_SEED
from app.engine.forecast import compute_day_over_day_changes

def test_day_over_day_changes_detection(tmp_path):
    """
    Verify detection of:
    - newly added deals
    - removed/dropped deals
    - modified ACV values
    """
    out_dir = str(tmp_path / "snapshots")
    snapshots = create_snapshots(count=1000, seed=DEFAULT_SEED, output_dir=out_dir)

    df_today = pd.read_csv(snapshots["today"])
    df_yesterday = pd.read_csv(snapshots["yesterday"])

    changes = compute_day_over_day_changes(df_today=df_today, df_yesterday=df_yesterday)

    assert "added_deals" in changes
    assert "removed_deals" in changes
    assert "modified_deals" in changes

    assert len(changes["added_deals"]) > 0
    assert len(changes["removed_deals"]) > 0
    assert len(changes["modified_deals"]) > 0

    # Total net ACV change calculation
    assert "net_acv_change" in changes
    assert isinstance(changes["net_acv_change"], float)
