import os
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from app.config import get_settings_config, get_rules_config
from app.ingestion.loader import ingest_csv_snapshot, get_snapshot_dataframe
from app.engine.forecast import compute_forecast_from_df, compute_day_over_day_changes
from app.engine.exporter import export_forecast_to_excel
from app.quality.checker import run_quality_checks
from app.reconciliation.mock_client import MockSalesCloudClient
from app.reconciliation.live_client import SalesCloudClient
from app.reconciliation.matcher import reconcile_forecast_with_sales_cloud
from scripts.generate_synthetic_data import create_snapshots

logger = logging.getLogger("forecast_automator.scheduler")

_scheduler = None

def run_daily_pipeline(
    snapshot_date: str = "2025-05-15",
    outbox_dir: str = None
) -> dict:
    """
    Automated daily job:
    1. Ensures daily snapshot is present and ingested
    2. Runs quality checks
    3. Reconciles against Sales Cloud
    4. Evaluates block_on_mismatch policy
    5. Exports Excel report to outbox/
    6. Logs audit recap
    """
    settings = get_settings_config()
    app_cfg = settings.get("app", {})
    sc_cfg = settings.get("sales_cloud", {})
    
    if not outbox_dir:
        outbox_dir = app_cfg.get("outbox_dir", "./outbox")
    os.makedirs(outbox_dir, exist_ok=True)

    snapshots_dir = app_cfg.get("snapshots_dir", "./data/snapshots")
    os.makedirs(snapshots_dir, exist_ok=True)
    
    today_csv = os.path.join(snapshots_dir, f"snapshot_{snapshot_date}.csv")
    yesterday_csv = os.path.join(snapshots_dir, "snapshot_2025-05-14.csv")

    if not os.path.exists(today_csv) or not os.path.exists(yesterday_csv):
        create_snapshots(count=2000, output_dir=snapshots_dir)

    # Ingest
    ingest_res = ingest_csv_snapshot(today_csv, snapshot_date=snapshot_date)
    
    # Load DataFrames
    df_today = get_snapshot_dataframe(snapshot_date)
    df_yesterday = get_snapshot_dataframe("2025-05-14")

    # Quality Checks
    quality_findings = run_quality_checks(df_today=df_today, df_yesterday=df_yesterday)

    # Reconciliation
    if sc_cfg.get("enabled", False):
        client = SalesCloudClient(enabled=True)
    else:
        client = MockSalesCloudClient()

    reconciliation_res = reconcile_forecast_with_sales_cloud(
        df_forecast=df_today,
        client=client,
        tolerance_usd=float(sc_cfg.get("per_order_tolerance_usd", 0.01)),
        max_retries=int(sc_cfg.get("max_retries", 3)),
        backoff_seconds=float(sc_cfg.get("retry_backoff_seconds", 1.0)),
        backoff_multiplier=float(sc_cfg.get("retry_backoff_multiplier", 2.0))
    )

    # Forecast calculation
    filtered_df, summary = compute_forecast_from_df(df_today)
    changes = compute_day_over_day_changes(df_today, df_yesterday)

    block_delivery = sc_cfg.get("block_on_mismatch", False) and reconciliation_res["status"] == "MISMATCH"

    report_path = None
    if not block_delivery:
        report_filename = f"daily_forecast_{snapshot_date}_{reconciliation_res['report_label']}.xlsx"
        report_path = os.path.join(outbox_dir, report_filename)
        export_forecast_to_excel(
            df=filtered_df,
            output_path=report_path,
            reconciliation_status=reconciliation_res["status"],
            report_label=reconciliation_res["report_label"]
        )

    # Structured recap
    recap = {
        "success": True,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "snapshot_date": snapshot_date,
        "report_path": report_path,
        "delivery_held": block_delivery,
        "summary": summary,
        "quality": quality_findings,
        "reconciliation": reconciliation_res,
        "day_over_day": changes
    }

    logger.info(
        f"[Daily Pipeline] Snapshot={snapshot_date} | Total ACV=${summary['grand_total_acv']:,.2f} | "
        f"Deals={summary['deal_count']} | Quality={quality_findings['status']} | "
        f"Recon={reconciliation_res['status']} ({reconciliation_res['report_label']}) | "
        f"Export={report_path}"
    )

    return recap

def start_scheduler():
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    settings = get_settings_config()
    sched_cfg = settings.get("scheduler", {})
    if not sched_cfg.get("enabled", True):
        logger.info("Scheduler disabled by configuration.")
        return None

    _scheduler = BackgroundScheduler()
    # Add daily job
    _scheduler.add_job(
        run_daily_pipeline,
        trigger="interval",
        seconds=sched_cfg.get("interval_seconds", 86400),
        id="daily_forecast_job",
        replace_existing=True
    )
    _scheduler.start()
    logger.info("APScheduler initialized and running.")
    return _scheduler

def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
