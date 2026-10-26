"""
Dormant SalesCloudClient for real IBM Sales Cloud integration.
Strictly disabled by default; requires explicit configuration & IBM approval.
Contains NO credentials or live endpoints.
"""

import os
from typing import Dict, Any, List, Optional, Tuple
from app.reconciliation.base import SalesSystemClient

class SalesCloudClient(SalesSystemClient):
    """
    Live adapter stub for IBM Sales Cloud.
    Disabled by default. Reads credentials exclusively from environment variables if enabled.
    """

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.api_endpoint = os.environ.get("SALES_CLOUD_API_ENDPOINT", "")
        self.api_key = os.environ.get("SALES_CLOUD_API_KEY", "")

    def health_check(self) -> bool:
        if not self.enabled:
            return False
        # Stub: When enabled with proper IBM authorization, performs ping
        return bool(self.api_endpoint and self.api_key)

    def fetch_signings(
        self,
        filters: Optional[Dict[str, Any]] = None,
        date_range: Optional[Tuple[str, str]] = None
    ) -> List[Dict[str, Any]]:
        if not self.enabled:
            raise RuntimeError(
                "SalesCloudClient is dormant and disabled. "
                "Enable only after IBM approval with synthetic or approved test credentials."
            )
        # Placeholder for approved live API call
        return []
