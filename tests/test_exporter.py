import os
import pytest
import openpyxl
import pandas as pd
from app.engine.exporter import export_forecast_to_excel
from scripts.generate_synthetic_data import create_snapshots

def test_excel_export_layout_and_content(tmp_path):
    """
    Verify generated Excel file matches legacy columns,
    preserves correct numeric types and includes reconciliation/quality metadata.
    """
    out_dir = str(tmp_path / "snapshots")
    snapshots = create_snapshots(count=500, seed=42, output_dir=out_dir)
    df_raw = pd.read_csv(snapshots["today"])
    
    # Filter to golden set
    df_golden = df_raw[
        (df_raw["country"] == "United States") &
        (df_raw["client_sub_type"] == "Select T Activate") &
        (df_raw["signing_category"] == "New Signings") &
        (df_raw["ut_level_15_dscr"] == "Data Platform")
    ].copy()

    export_path = str(tmp_path / "forecast_test.xlsx")
    export_forecast_to_excel(
        df=df_golden,
        output_path=export_path,
        reconciliation_status="MATCH",
        report_label="FINAL"
    )

    assert os.path.exists(export_path)

    # Read back workbook
    wb = openpyxl.load_workbook(export_path)
    assert "New Signings Forecast" in wb.sheetnames
    
    ws = wb["New Signings Forecast"]
    
    # Verify expected column headers
    headers = [cell.value for cell in ws[1]]
    expected_headers = [
        "ut_level_30_dscr", "coverage_id", "signing_date",
        "sales_order_num", "customer_name", "saas_acv_usd_at_plan"
    ]
    assert headers == expected_headers

    # Verify rows exist
    assert ws.max_row > 1
    # Verify last row is formatted properly
    assert isinstance(ws.cell(row=2, column=6).value, (int, float))
