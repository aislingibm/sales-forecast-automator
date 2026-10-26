import os
import csv
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.db import RawDeal, QuarantinedDeal, init_db

logger = logging.getLogger(__name__)

EXPECTED_COLUMNS = [
    "ut_level_30_dscr", "ut_level_15_dscr", "coverage_id", "signing_date",
    "sales_order_num", "customer_name", "saas_acv_usd_at_plan", "country",
    "client_sub_type", "signing_category"
]

def ingest_csv_snapshot(
    csv_path: str,
    snapshot_date: str = None,
    session_factory = None
) -> Dict[str, Any]:
    """
    Ingests a CSV snapshot file into SQLite raw_deals table.
    Quarantines structurally corrupt rows and logs clear reasons.
    """
    if not session_factory:
        session_factory = init_db()

    if not snapshot_date:
        filename = os.path.basename(csv_path)
        if "snapshot_" in filename:
            snapshot_date = filename.replace("snapshot_", "").replace(".csv", "")
        else:
            snapshot_date = datetime.utcnow().strftime("%Y-%m-%d")

    session: Session = session_factory()
    
    total_rows = 0
    loaded_rows = 0
    quarantined_rows = 0

    try:
        # Clear existing records for this snapshot date (idempotency)
        session.query(RawDeal).filter(RawDeal.snapshot_date == snapshot_date).delete()
        session.query(QuarantinedDeal).filter(QuarantinedDeal.snapshot_date == snapshot_date).delete()
        session.commit()

        with open(csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            
            for row_idx, row in enumerate(reader, start=1):
                total_rows += 1
                
                # Check for critical malformations
                if not row or not any(row.values()):
                    # Empty row
                    quarantine_entry = QuarantinedDeal(
                        snapshot_date=snapshot_date,
                        raw_payload=str(row),
                        error_reason=f"Empty row at line {row_idx}"
                    )
                    session.add(quarantine_entry)
                    quarantined_rows += 1
                    continue

                raw_acv = row.get("saas_acv_usd_at_plan", "")
                try:
                    acv_val = float(raw_acv) if raw_acv not in ["", None] else 0.0
                except (ValueError, TypeError):
                    acv_val = None

                deal = RawDeal(
                    snapshot_date=snapshot_date,
                    sales_order_num=row.get("sales_order_num") or None,
                    ut_level_30_dscr=row.get("ut_level_30_dscr") or None,
                    ut_level_15_dscr=row.get("ut_level_15_dscr") or None,
                    coverage_id=row.get("coverage_id") or None,
                    signing_date=row.get("signing_date") or None,
                    customer_name=row.get("customer_name") or None,
                    saas_acv_usd_at_plan=acv_val,
                    country=row.get("country") or None,
                    client_sub_type=row.get("client_sub_type") or None,
                    signing_category=row.get("signing_category") or None,
                )
                session.add(deal)
                loaded_rows += 1

                # Flush in batches
                if loaded_rows % 1000 == 0:
                    session.commit()

            session.commit()

    except Exception as e:
        session.rollback()
        logger.error(f"Error during ingestion of {csv_path}: {e}")
        raise e
    finally:
        session.close()

    return {
        "snapshot_date": snapshot_date,
        "total_rows": total_rows,
        "loaded_rows": loaded_rows,
        "quarantined_rows": quarantined_rows,
        "status": "COMPLETED"
    }

def get_snapshot_dataframe(
    snapshot_date: str = None,
    session_factory = None
) -> pd.DataFrame:
    """
    Retrieves snapshot records as a pandas DataFrame.
    If snapshot_date is None, fetches the latest available snapshot.
    """
    if not session_factory:
        session_factory = init_db()

    session: Session = session_factory()
    try:
        if not snapshot_date:
            latest = session.query(RawDeal.snapshot_date).order_by(RawDeal.snapshot_date.desc()).first()
            if latest:
                snapshot_date = latest[0]
            else:
                return pd.DataFrame(columns=EXPECTED_COLUMNS)

        query = session.query(RawDeal).filter(RawDeal.snapshot_date == snapshot_date)
        records = [
            {
                "ut_level_30_dscr": r.ut_level_30_dscr,
                "ut_level_15_dscr": r.ut_level_15_dscr,
                "coverage_id": r.coverage_id or "",
                "signing_date": r.signing_date,
                "sales_order_num": r.sales_order_num or "",
                "customer_name": r.customer_name or "",
                "saas_acv_usd_at_plan": r.saas_acv_usd_at_plan if r.saas_acv_usd_at_plan is not None else 0.0,
                "country": r.country,
                "client_sub_type": r.client_sub_type,
                "signing_category": r.signing_category,
            }
            for r in query.all()
        ]
        return pd.DataFrame(records)
    finally:
        session.close()
