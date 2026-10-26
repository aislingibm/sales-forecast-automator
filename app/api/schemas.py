from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class DealRecord(BaseModel):
    ut_level_30_dscr: Optional[str] = None
    coverage_id: Optional[str] = None
    signing_date: Optional[str] = None
    sales_order_num: Optional[str] = None
    customer_name: Optional[str] = None
    saas_acv_usd_at_plan: float = 0.0

class SummaryStats(BaseModel):
    grand_total_acv: float = 0.0
    deal_count: int = 0
    avg_deal_size: float = 0.0

class ProductBreakdown(BaseModel):
    ut_level_30_dscr: str
    total_acv: float
    deal_count: int

class GroupedItem(BaseModel):
    group_key: str
    total_acv: float
    deal_count: int

class ForecastResponse(BaseModel):
    summary: SummaryStats
    ut30_breakdown: List[Dict[str, Any]] = []
    grouped_data: List[GroupedItem] = []
    deals: List[Dict[str, Any]] = []

class QualityFinding(BaseModel):
    status: str
    duplicates_count: int
    missing_coverage_id_count: int
    invalid_acv_count: int
    dod_swing_pct: float
    issues: List[str]

class ChangesResponse(BaseModel):
    added_deals: List[Dict[str, Any]] = []
    removed_deals: List[Dict[str, Any]] = []
    modified_deals: List[Dict[str, Any]] = []
    net_acv_change: float = 0.0
    pct_change: float = 0.0

class ReconciliationResponse(BaseModel):
    status: str
    report_label: str
    verified: bool
    forecast_total_usd: float
    sales_cloud_total_usd: float
    variance_usd: float
    affected_orders_count: int

class VarianceDetailItem(BaseModel):
    sales_order_num: str
    customer_name: Optional[str] = ""
    forecast_acv: Optional[float] = None
    sales_cloud_acv: Optional[float] = None
    variance_usd: float = 0.0
    variance_type: str
    details: str

class ReconciliationDetailsResponse(BaseModel):
    status: str
    report_label: str
    total_variances: int
    variances: List[VarianceDetailItem]
