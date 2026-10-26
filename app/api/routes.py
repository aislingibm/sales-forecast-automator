import os
import io
import tempfile
import pandas as pd
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import Response, StreamingResponse
from app.ingestion.loader import get_snapshot_dataframe
from scripts.generate_synthetic_data import get_as_of_date, previous_snapshot_date
from app.engine.forecast import compute_forecast_from_df, compute_day_over_day_changes
from app.engine.exporter import export_forecast_to_excel
from app.quality.checker import run_quality_checks
from app.reconciliation.mock_client import MockSalesCloudClient
from app.reconciliation.matcher import reconcile_forecast_with_sales_cloud
from app.api.schemas import (
    ForecastResponse,
    QualityFinding,
    ChangesResponse,
    ReconciliationResponse,
    ReconciliationDetailsResponse,
    VarianceDetailItem
)

router = APIRouter()

@router.get("/health", tags=["System"])
def health_check():
    """Liveness probe."""
    return {"status": "healthy", "service": "Sales Forecast Automator"}

@router.get("/forecast", response_model=ForecastResponse, tags=["Forecast"])
def get_forecast(
    snapshot_date: Optional[str] = Query(None, description="Snapshot date YYYY-MM-DD"),
    country: Optional[str] = Query(None, description="Country filter"),
    client_sub_type: Optional[str] = Query(None, description="Client sub-type filter"),
    signing_category: Optional[str] = Query(None, description="Signing category filter"),
    ut_level_15: Optional[str] = Query(None, description="UT Level 15 (Product Area) filter"),
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    group_by: Optional[str] = Query(None, description="Group by: day, week, month, quarter, ut_level_30, customer")
):
    """Retrieve filtered forecast metrics, aggregated breakdowns, and deal records."""
    df = get_snapshot_dataframe(snapshot_date)
    
    custom_filters = {}
    if country is not None:
        custom_filters["country"] = country
    if client_sub_type is not None:
        custom_filters["client_sub_type"] = client_sub_type
    if signing_category is not None:
        custom_filters["signing_category"] = signing_category
    if ut_level_15 is not None:
        custom_filters["ut_level_15_dscr"] = ut_level_15

    result_df, summary = compute_forecast_from_df(
        df=df,
        custom_filters=custom_filters if custom_filters else None,
        group_by=group_by,
        date_from=date_from,
        date_to=date_to
    )

    deals = result_df.to_dict(orient="records") if not result_df.empty else []

    return {
        "summary": summary,
        "ut30_breakdown": summary.get("ut30_breakdown", []),
        "grouped_data": summary.get("grouped_data", []),
        "deals": deals
    }

@router.get("/forecast/export", tags=["Forecast"])
def export_forecast(
    format: str = Query("xlsx", pattern="^(xlsx|csv)$", description="Export file format"),
    snapshot_date: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    client_sub_type: Optional[str] = Query(None),
    signing_category: Optional[str] = Query(None),
    ut_level_15: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """Download forecast report in legacy Excel layout or clean CSV."""
    df = get_snapshot_dataframe(snapshot_date)
    
    custom_filters = {}
    if country:
        custom_filters["country"] = country
    if client_sub_type:
        custom_filters["client_sub_type"] = client_sub_type
    if signing_category:
        custom_filters["signing_category"] = signing_category
    if ut_level_15:
        custom_filters["ut_level_15_dscr"] = ut_level_15

    result_df, summary = compute_forecast_from_df(
        df=df,
        custom_filters=custom_filters,
        date_from=date_from,
        date_to=date_to
    )

    if format == "csv":
        csv_buffer = io.StringIO()
        result_df.to_csv(csv_buffer, index=False)
        return Response(
            content=csv_buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=forecast_export.csv"}
        )

    # Excel export
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        export_forecast_to_excel(result_df, tmp_path)
        with open(tmp_path, "rb") as f:
            xlsx_content = f.read()
        return Response(
            content=xlsx_content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=forecast_legacy_export.xlsx"}
        )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.get("/quality", response_model=QualityFinding, tags=["Data Quality"])
def get_quality(snapshot_date: Optional[str] = Query(None)):
    """Run data quality engine and return anomalies."""
    df_today = get_snapshot_dataframe(snapshot_date)
    df_yesterday = get_snapshot_dataframe(previous_snapshot_date(snapshot_date))
    
    findings = run_quality_checks(df_today=df_today, df_yesterday=df_yesterday)
    return findings

@router.get("/changes", response_model=ChangesResponse, tags=["Forecast"])
def get_changes(since: str = Query("yesterday", description="Comparison snapshot reference")):
    """Get deals added, removed, or modified since yesterday."""
    df_today = get_snapshot_dataframe(get_as_of_date().isoformat())
    df_yesterday = get_snapshot_dataframe(previous_snapshot_date())
    
    changes = compute_day_over_day_changes(df_today=df_today, df_yesterday=df_yesterday)
    return changes

@router.get("/reconciliation", response_model=ReconciliationResponse, tags=["Reconciliation"])
def get_reconciliation(snapshot_date: Optional[str] = Query(None)):
    """Cross-check forecast against IBM Sales Cloud System of Record."""
    df = get_snapshot_dataframe(snapshot_date)
    client = MockSalesCloudClient()
    result = reconcile_forecast_with_sales_cloud(df_forecast=df, client=client)
    return result

@router.get("/reconciliation/details", response_model=ReconciliationDetailsResponse, tags=["Reconciliation"])
def get_reconciliation_details(
    snapshot_date: Optional[str] = Query(None),
    variance_type: Optional[str] = Query(None)
):
    """Retrieve row-level itemized reconciliation variances."""
    df = get_snapshot_dataframe(snapshot_date)
    client = MockSalesCloudClient()
    result = reconcile_forecast_with_sales_cloud(df_forecast=df, client=client)
    
    variances_by_type = result.get("variances_by_type", {})
    all_items = []
    
    for vtype, items in variances_by_type.items():
        if variance_type and variance_type != vtype:
            continue
        for it in items:
            all_items.append(VarianceDetailItem(
                sales_order_num=it.get("sales_order_num", ""),
                customer_name=it.get("customer_name", ""),
                forecast_acv=it.get("forecast_acv"),
                sales_cloud_acv=it.get("sales_cloud_acv"),
                variance_usd=it.get("variance_usd", 0.0),
                variance_type=vtype,
                details=it.get("details", "")
            ))

    return {
        "status": result.get("status", "MATCH"),
        "report_label": result.get("report_label", "FINAL"),
        "total_variances": len(all_items),
        "variances": all_items
    }
