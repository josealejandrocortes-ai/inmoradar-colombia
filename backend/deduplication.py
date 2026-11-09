"""
Cross-Portal Deduplication Engine for Colombian Real Estate.
Detects identical properties listed across multiple portals (Finca Raíz, Metrocuadrado, etc.)
with differing prices, titles, or broker agencies.
"""

from typing import List, Dict, Tuple
import math
from .models import PropertyListing


class DeduplicationEngine:
    """
    Groups properties that share:
    - Same City and same Neighborhood / Localidad
    - Same Estrato
    - Same number of bedrooms and bathrooms
    - Area within +/- 4% tolerance
    - Price within +/- 15% (brokers often list with differing commissions)
    """

    @staticmethod
    def _is_similar_location(p1: PropertyListing, p2: PropertyListing) -> bool:
        if p1.location.city.lower() != p2.location.city.lower():
            return False
        n1 = p1.location.neighborhood.lower()
        n2 = p2.location.neighborhood.lower()
        return (n1 == n2) or (n1 in n2) or (n2 in n1)

    @classmethod
    def are_likely_duplicates(cls, p1: PropertyListing, p2: PropertyListing) -> Tuple[bool, float, str]:
        # Can't duplicate itself on the same portal with same external ID
        if p1.portal == p2.portal and p1.external_id == p2.external_id:
            return False, 0.0, "Mismo anuncio"

        if not cls._is_similar_location(p1, p2):
            return False, 0.0, "Diferente ubicación"

        # Check estrato
        if p1.stratum != p2.stratum:
            return False, 0.0, "Diferente estrato"

        # Check bedrooms and bathrooms
        if p1.bedrooms != p2.bedrooms or p1.bathrooms != p2.bathrooms:
            return False, 0.0, "Diferente distribución de alcobas/baños"

        # Check area tolerance (+/- 5%)
        a1 = p1.built_area_m2 or 1.0
        a2 = p2.built_area_m2 or 1.0
        area_diff_pct = abs(a1 - a2) / max(a1, a2)
        if area_diff_pct > 0.06:
            return False, 0.0, f"Diferencia de área ({a1}m² vs {a2}m²)"

        # Check parking
        if abs(p1.parking_spots - p2.parking_spots) > 0:
            # Sometimes one broker lists 0 if not sure, so we allow 1 diff with penalty
            pass

        # Check price tolerance (+/- 15%)
        price_diff_pct = abs(p1.price_cop - p2.price_cop) / max(p1.price_cop, p2.price_cop)
        if price_diff_pct > 0.18:
            return False, 0.0, "Diferencia de precio superior al 18%"

        # Similarity score calculation (0 to 1)
        sim_score = 1.0 - (area_diff_pct * 0.4 + price_diff_pct * 0.6)
        reason = f"Coincidencia alta ({sim_score*100:.0f}%): Misma zona ({p1.location.neighborhood}), {p1.bedrooms} alcobas, área ~{a1:.0f}m²."
        return True, sim_score, reason

    @classmethod
    def cluster_listings(cls, listings: List[PropertyListing]) -> List[Dict]:
        """
        Clusters duplicates and returns unified property clusters with price discrepancy insights.
        """
        clusters: List[Dict] = []
        visited = set()

        for i, prop in enumerate(listings):
            if prop.id in visited:
                continue

            current_cluster = [prop]
            visited.add(prop.id)

            for j in range(i + 1, len(listings)):
                other_prop = listings[j]
                if other_prop.id in visited:
                    continue

                is_dup, score, reason = cls.are_likely_duplicates(prop, other_prop)
                if is_dup and score >= 0.80:
                    current_cluster.append(other_prop)
                    visited.add(other_prop.id)

            prices = [p.price_cop for p in current_cluster]
            min_price = min(prices)
            max_price = max(prices)
            price_discrepancy_cop = max_price - min_price
            best_deal_portal = next(p.portal.value for p in current_cluster if p.price_cop == min_price)

            clusters.append({
                "cluster_id": f"cluster_{prop.id}",
                "canonical_listing": prop,
                "all_listings": current_cluster,
                "sources_count": len(current_cluster),
                "portals": list(set(p.portal.value for p in current_cluster)),
                "min_price_cop": min_price,
                "max_price_cop": max_price,
                "price_discrepancy_cop": price_discrepancy_cop,
                "best_deal_portal": best_deal_portal,
                "negotiation_tip": (
                    f"¡Aviso duplicado encontrado en {len(current_cluster)} portales! "
                    f"Se vende ${price_discrepancy_cop:,.0f} COP más barato en {best_deal_portal}."
                    if price_discrepancy_cop > 0 else "Publicación única o con precio homogéneo."
                )
            })

        return clusters
