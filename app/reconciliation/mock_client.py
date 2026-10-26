"""
In-process Mock Sales Cloud Client with deterministic planted variances.
Implements SalesSystemClient.
"""

from typing import Dict, Any, List, Optional, Tuple
from app.reconciliation.base import SalesSystemClient
from scripts.generate_synthetic_data import (
    generate_base_records,
    generate_mock_sales_cloud_dataset,
    inject_quality_anomalies,
    get_as_of_date,
    DEFAULT_SEED
)

class MockSalesCloudClient(SalesSystemClient):
    """
    Deterministic in-process mock for IBM Sales Cloud.
    Generates SoR data with known planted variances for reconciliation tests.
    """

    def __init__(
        self,
        seed: int = DEFAULT_SEED,
        row_count: int = 2000,
        simulate_failure: bool = False
    ):
        self.seed = seed
        self.row_count = row_count
        self.simulate_failure = simulate_failure
        self.call_count = 0
        self.failure_countdown = 0

    def set_transient_failure(self, fail_times: int):
        """Simulate transient network failure for testing retry/backoff."""
        self.failure_countdown = fail_times

    def health_check(self) -> bool:
        if self.simulate_failure or self.failure_countdown > 0:
            return False
        return True

    def fetch_signings(
        self,
        filters: Optional[Dict[str, Any]] = None,
        date_range: Optional[Tuple[str, str]] = None
    ) -> List[Dict[str, Any]]:
        self.call_count += 1
        
        if self.simulate_failure:
            raise ConnectionError("Mock Sales Cloud is currently unavailable (simulated outage).")
            
        if self.failure_countdown > 0:
            self.failure_countdown -= 1
            raise ConnectionError("Mock Sales Cloud transient network timeout.")

        # Generate forecast records with anomalies to derive corresponding mock SoR dataset
        import random
        as_of = get_as_of_date()
        base_records = generate_base_records(count=self.row_count, base_date=as_of, seed=self.seed)
        records_today, _ = inject_quality_anomalies(base_records, random.Random(self.seed))
        sc_records, _ = generate_mock_sales_cloud_dataset(records_today, seed=self.seed, as_of=as_of)

        # Apply optional filters
        if filters:
            filtered = []
            for r in sc_records:
                match = True
                for k, v in filters.items():
                    if r.get(k) != v:
                        match = False
                        break
                if match:
                    filtered.append(r)
            sc_records = filtered

        # Apply optional date range
        if date_range:
            start_dt, end_dt = date_range
            sc_records = [
                r for r in sc_records
                if start_dt <= r["signing_date"] <= end_dt
            ]

        return sc_records
