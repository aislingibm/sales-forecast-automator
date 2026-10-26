from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

class SalesSystemClient(ABC):
    """
    Abstract connector interface for Sales Systems (e.g., IBM Sales Cloud).
    """

    @abstractmethod
    def fetch_signings(
        self,
        filters: Optional[Dict[str, Any]] = None,
        date_range: Optional[Tuple[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch signing records matching the filter criteria.
        Returns rows conforming to the standard synthetic schema.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check connectivity to the sales system.
        """
        pass
