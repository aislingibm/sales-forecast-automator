import pytest
import pandas as pd
from app.reconciliation.mock_client import MockSalesCloudClient
from app.reconciliation.live_client import SalesCloudClient
from app.reconciliation.matcher import reconcile_forecast_with_sales_cloud
from scripts.generate_synthetic_data import create_snapshots

def test_dormant_live_client():
    """Verify live client is dormant and raises error without approval."""
    client = SalesCloudClient(enabled=False)
    assert client.health_check() is False
    with pytest.raises(RuntimeError):
        client.fetch_signings()

def test_mock_sales_cloud_planted_variances(tmp_path):
    """
    Verify 3-level reconciliation engine identifies all planted variances:
    1. Grand total comparison
    2. Date & UT30 grain
    3. Order-level join on sales_order_num
    """
    out_dir = str(tmp_path / "snapshots")
    snapshots = create_snapshots(count=1000, seed=42, output_dir=out_dir)
    df_forecast = pd.read_csv(snapshots["today"])

    mock_client = MockSalesCloudClient(seed=42, row_count=1000)
    
    result = reconcile_forecast_with_sales_cloud(
        df_forecast=df_forecast,
        client=mock_client,
        tolerance_usd=0.01
    )

    assert result["status"] == "MISMATCH"
    assert result["report_label"] == "CHECK"
    assert result["affected_orders_count"] > 0
    
    variances = result["variances_by_type"]
    assert len(variances["ONLY_IN_FORECAST"]) == 3
    assert len(variances["ONLY_IN_SALES_CLOUD"]) == 2
    assert len(variances["ACV_MISMATCH"]) == 3
    assert len(variances["ATTRIBUTE_MISMATCH"]) == 3

def test_reconciliation_retry_with_backoff():
    """Verify retry with backoff succeeds when transient outage resolves."""
    mock_client = MockSalesCloudClient(seed=42, row_count=500)
    mock_client.set_transient_failure(fail_times=2)
    
    df_forecast = pd.DataFrame([
        {
            "sales_order_num": "SO-000001",
            "coverage_id": "COV-00001",
            "saas_acv_usd_at_plan": 50000.0,
            "signing_date": "2025-05-15",
            "country": "United States",
            "client_sub_type": "Select T Activate",
            "signing_category": "New Signings",
            "ut_level_15_dscr": "Data Platform",
            "ut_level_30_dscr": "watsonx.data Core",
            "customer_name": "Acme Test 1"
        }
    ])

    result = reconcile_forecast_with_sales_cloud(
        df_forecast=df_forecast,
        client=mock_client,
        max_retries=3,
        backoff_seconds=0.05
    )
    
    assert result["status"] in ["MATCH", "MISMATCH"]
    assert result["verified"] is True

def test_reconciliation_outage_fallback():
    """Verify persistent outage returns 'Not verified' label without unhandled exception."""
    mock_client = MockSalesCloudClient(simulate_failure=True)
    df_forecast = pd.DataFrame()

    result = reconcile_forecast_with_sales_cloud(
        df_forecast=df_forecast,
        client=mock_client,
        max_retries=2,
        backoff_seconds=0.01
    )

    assert result["status"] == "UNAVAILABLE"
    assert result["report_label"] == "Not verified"
    assert result["verified"] is False
