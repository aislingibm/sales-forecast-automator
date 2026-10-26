import os
import pytest
from app.scheduler.runner import run_daily_pipeline

def test_daily_pipeline_run(tmp_path):
    """
    Verify scheduled daily pipeline execution:
    - reads snapshot
    - runs forecast computation & quality check
    - reconciles Sales Cloud
    - produces .xlsx in outbox directory
    """
    outbox_dir = str(tmp_path / "outbox")
    os.makedirs(outbox_dir, exist_ok=True)

    result = run_daily_pipeline(outbox_dir=outbox_dir)

    assert result["success"] is True
    assert "report_path" in result
    assert os.path.exists(result["report_path"])
    assert "summary" in result
    assert "reconciliation" in result
    assert result["summary"]["deal_count"] > 0
