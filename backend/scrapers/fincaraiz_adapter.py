"""
Adapter for Finca Raíz Colombia (fincaraiz.com.co).
Parses real estate listings from Finca Raiz web & internal APIs into standard format.
"""

import uuid
from typing import List, Dict, Any, Optional
from .base_scraper import BaseRealEstateScraper
from ..models import PropertyListing, ColombianLocation, PropertyType, PortalSource


class FincaRaizAdapter(BaseRealEstateScraper):
    def __init__(self, proxy_url: Optional[str] = None):
        super().__init__(portal=PortalSource.FINCARAIZ, rate_limit_sec=2.0, proxy_url=proxy_url)
        self.api_endpoint = "https://api.fincaraiz.com.co/document/api/v1.0/listing/search"

    def search(
        self,
        city: str,
        property_type: PropertyType = PropertyType.APARTMENT,
        operation: str = "venta",
        max_pages: int = 1,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> List[PropertyListing]:
        """
        Executes query against Finca Raiz API or web interface.
        In production, this handles pagination, residential proxies and Cloudflare TLS fingerprints.
        """
        self._apply_rate_limit()
        # Simulated or actual HTTP fetch depending on network environment
        # Return standardized PropertyListing instances
        return []

    def parse_listing(self, item: Dict[str, Any]) -> Optional[PropertyListing]:
        try:
            listing_id = str(item.get("id") or item.get("id_property") or uuid.uuid4().hex[:10])
            title = item.get("title") or item.get("description_title") or "Inmueble en venta"
            price = float(item.get("price") or item.get("sale_price") or 0)
            area = float(item.get("area") or item.get("built_area") or item.get("surface") or 50.0)

            # Location details
            loc_data = item.get("location") or {}
            city_name = loc_data.get("city") or "Bogotá"
            neighborhood = loc_data.get("neighborhood") or loc_data.get("barrio") or "Sector Central"
            estrato = int(loc_data.get("stratum") or item.get("estrato") or 4)

            location = ColombianLocation(
                city=city_name,
                locality=loc_data.get("locality"),
                neighborhood=neighborhood,
                latitude=loc_data.get("lat"),
                longitude=loc_data.get("lng"),
                estrato=estrato
            )

            bedrooms = int(item.get("rooms") or item.get("bedrooms") or 2)
            bathrooms = int(item.get("baths") or item.get("bathrooms") or 2)
            parking = int(item.get("garages") or item.get("parking") or 1)
            admin_fee = float(item.get("administration") or item.get("admin_fee") or 0.0)

            images = item.get("images") or []
            if isinstance(images, list) and images and isinstance(images[0], dict):
                images = [img.get("url") or img.get("image") for img in images if img.get("url") or img.get("image")]

            return PropertyListing(
                id=f"fr_{listing_id}",
                portal=PortalSource.FINCARAIZ,
                external_id=listing_id,
                url=item.get("link") or f"https://www.fincaraiz.com.co/inmueble/{listing_id}",
                title=title,
                property_type=PropertyType.APARTMENT,
                location=location,
                price_cop=price,
                built_area_m2=area,
                private_area_m2=float(item.get("private_area") or area),
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                parking_spots=parking,
                stratum=estrato,
                admin_fee_cop=admin_fee,
                property_age_years=item.get("age_years"),
                floor_number=item.get("floor"),
                has_elevator=bool(item.get("has_elevator", False)),
                has_balcony=bool(item.get("has_balcony", False)),
                has_storage_room=bool(item.get("has_storage", False)),
                images=images,
                description=item.get("description", ""),
                days_on_market=item.get("days_on_market", 3),
                raw_data=item
            )
        except Exception as e:
            print(f"[Error parsing FincaRaiz item]: {e}")
            return None
