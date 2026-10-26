import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, Index
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

def _utc_now():
    return datetime.now(timezone.utc)

class RawDeal(Base):
    """
    Raw snapshot table storing ingested sales records.
    Uses surrogate 'id' primary key to allow duplicate sales_order_num records.
    """
    __tablename__ = "raw_deals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(String(32), nullable=False, index=True)
    sales_order_num = Column(String(64), nullable=True, index=True)
    ut_level_30_dscr = Column(String(128), nullable=True)
    ut_level_15_dscr = Column(String(64), nullable=True)
    coverage_id = Column(String(64), nullable=True)
    signing_date = Column(String(32), nullable=True, index=True)
    customer_name = Column(String(128), nullable=True)
    saas_acv_usd_at_plan = Column(Float, nullable=True)
    country = Column(String(64), nullable=True)
    client_sub_type = Column(String(64), nullable=True)
    signing_category = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=_utc_now)

    __table_args__ = (
        Index("idx_snapshot_filters", "snapshot_date", "country", "client_sub_type", "signing_category", "ut_level_15_dscr"),
    )

class QuarantinedDeal(Base):
    """
    Quarantined records that failed CSV parsing or had invalid schema structure.
    """
    __tablename__ = "quarantined_deals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(String(32), nullable=False, index=True)
    raw_payload = Column(Text, nullable=False)
    error_reason = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=_utc_now)

class PipelineRun(Base):
    """
    Audit log of daily pipeline runs.
    """
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_timestamp = Column(DateTime, default=_utc_now)
    snapshot_date = Column(String(32), nullable=False)
    total_rows = Column(Integer, default=0)
    quarantined_rows = Column(Integer, default=0)
    status = Column(String(32), default="SUCCESS")
    reconciliation_status = Column(String(32), default="MATCH")
    report_path = Column(String(255), nullable=True)

def get_engine(db_path: str = None):
    if not db_path:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        db_path = f"sqlite:///{os.path.join(data_dir, 'forecast.db')}"
    return create_engine(db_path, connect_args={"check_same_thread": False})

def init_db(db_path: str = None):
    engine = get_engine(db_path)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
