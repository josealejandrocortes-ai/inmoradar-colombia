"""
Base Scraper Architecture for Colombian Portals.
Includes rate limiting, user-agent rotation, proxy hook, and standardized output.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import time
import random
from ..models import PropertyListing, ColombianLocation, PropertyType, PortalSource


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
]


class BaseRealEstateScraper(ABC):
    def __init__(self, portal: PortalSource, rate_limit_sec: float = 2.0, proxy_url: Optional[str] = None):
        self.portal = portal
        self.rate_limit_sec = rate_limit_sec
        self.proxy_url = proxy_url
        self.last_request_time = 0.0

    def _apply_rate_limit(self):
        elapsed = time.time() - self.last_request_time
        target_sleep = self.rate_limit_sec + random.uniform(0.5, 1.5)
        if elapsed < target_sleep:
            time.sleep(target_sleep - elapsed)
        self.last_request_time = time.time()

    def get_random_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
            "Cache-Control": "no-cache",
        }

    @abstractmethod
    def search(
        self,
        city: str,
        property_type: PropertyType = PropertyType.APARTMENT,
        operation: str = "venta",
        max_pages: int = 3,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> List[PropertyListing]:
        """Fetch listings for given criteria."""
        pass

    @abstractmethod
    def parse_listing(self, raw_data: Dict[str, Any]) -> Optional[PropertyListing]:
        """Convert raw portal JSON or HTML to canonical PropertyListing."""
        pass
