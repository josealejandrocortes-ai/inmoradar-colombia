"""
Opportunity Valuation Engine for Colombian Real Estate.
Computes market discounts, gross & net rental yields, and composite opportunity scores.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from .models import (
    PropertyListing,
    OpportunityAnalysis,
    InvestmentStrategy,
    PropertyType
)


class OpportunityEngine:
    def __init__(self, benchmarks_path: Optional[str] = None):
        if not benchmarks_path:
            benchmarks_path = str(
                Path(__file__).parent.parent / "data" / "colombia_market_benchmarks.json"
            )
        self.benchmarks_path = benchmarks_path
        self.benchmarks: Dict[str, Dict] = {}
        self._load_benchmarks()

    def _make_key(self, city: str, neighborhood: str, estrato: int) -> str:
        return f"{city.strip().lower()}:{neighborhood.strip().lower()}:{estrato}"

    def _load_benchmarks(self):
        try:
            with open(self.benchmarks_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("benchmarks", []):
                    key = self._make_key(item["city"], item["neighborhood"], item["estrato"])
                    self.benchmarks[key] = item
        except Exception as e:
            print(f"[Warning] Could not load benchmarks from {self.benchmarks_path}: {e}")

    def find_benchmark(self, city: str, neighborhood: str, estrato: int) -> Optional[Dict]:
        # Exact match
        key = self._make_key(city, neighborhood, estrato)
        if key in self.benchmarks:
            return self.benchmarks[key]

        # Fuzzy neighborhood / city match
        for b_key, b_data in self.benchmarks.items():
            b_city, b_neigh, b_estr = b_key.split(":")
            if b_city == city.lower() and (
                neighborhood.lower() in b_neigh or b_neigh in neighborhood.lower()
            ):
                return b_data

        # Fallback to city + estrato average
        city_matches = [
            b for k, b in self.benchmarks.items()
            if k.startswith(f"{city.lower()}:") and b["estrato"] == estrato
        ]
        if city_matches:
            avg_median = sum(m["median_price_m2"] for m in city_matches) / len(city_matches)
            avg_rent_m2 = sum(m["estimated_monthly_rent_m2"] for m in city_matches) / len(city_matches)
            return {
                "city": city,
                "neighborhood": f"Promedio {city} Estrato {estrato}",
                "estrato": estrato,
                "median_price_m2": avg_median,
                "estimated_monthly_rent_m2": avg_rent_m2,
                "total_samples": 50,
                "_is_synthetic": True
            }

        return None

    def analyze_property(self, prop: PropertyListing) -> OpportunityAnalysis:
        area = prop.built_area_m2 or prop.private_area_m2 or 1.0
        actual_price_m2 = prop.price_cop / area
        estrato = prop.stratum or prop.location.estrato or 4
        benchmark = self.find_benchmark(prop.location.city, prop.location.neighborhood, estrato)

        reasons: List[str] = []
        risks: List[str] = []

        if not benchmark:
            # Fallback if no benchmark available
            benchmark_price_m2 = actual_price_m2
            est_rent_m2 = actual_price_m2 * 0.0055
            confidence = "Baja"
            risks.append("No se encontró suficiente información histórica de la zona para benchmark exacto.")
        else:
            benchmark_price_m2 = benchmark["median_price_m2"]
            est_rent_m2 = benchmark.get("estimated_monthly_rent_m2", benchmark_price_m2 * 0.0055)
            confidence = "Media" if benchmark.get("_is_synthetic") else "Alta"

        # 1. Discount vs Market Median
        discount_pct = ((benchmark_price_m2 - actual_price_m2) / benchmark_price_m2) * 100.0
        fair_market_value_cop = benchmark_price_m2 * area

        # 2. Rental Yields
        estimated_monthly_rent_cop = est_rent_m2 * area
        gross_annual_rent = estimated_monthly_rent_cop * 12.0
        gross_yield_pct = (gross_annual_rent / prop.price_cop) * 100.0 if prop.price_cop > 0 else 0.0

        # Colombian Net Yield Deductions:
        # - Predial anual: ~0.8% - 1.2% del avalúo catastral (estimado ~0.7% del valor comercial)
        # - Vacancia y gestión inmobiliaria (8% del canon)
        # - Administración mensual pagada por el propietario (o asumida)
        annual_predial_est = prop.price_cop * 0.007
        effective_annual_rent = gross_annual_rent * 0.92
        annual_admin_fees = (prop.admin_fee_cop or 0.0) * 12.0
        net_annual_income = effective_annual_rent - annual_predial_est - annual_admin_fees
        net_yield_pct = (net_annual_income / prop.price_cop) * 100.0 if prop.price_cop > 0 else 0.0

        # 3. Opportunity Scoring Algorithm (0 - 100)
        # Component A: Discount vs Sector (0 - 40 points)
        if discount_pct >= 30.0:
            score_discount = 40.0
            reasons.append(f"¡Excelente precio! {discount_pct:.1f}% por debajo de la mediana del barrio.")
        elif discount_pct >= 20.0:
            score_discount = 32.0 + (discount_pct - 20.0) * 0.8
            reasons.append(f"Gran descuento de {discount_pct:.1f}% respecto al m² promedio del sector.")
        elif discount_pct >= 10.0:
            score_discount = 20.0 + (discount_pct - 10.0) * 1.2
            reasons.append(f"Precio competitivo: {discount_pct:.1f}% por debajo del mercado.")
        elif discount_pct >= 0.0:
            score_discount = 10.0 + discount_pct
        else:
            score_discount = max(0.0, 10.0 + discount_pct * 0.5)
            risks.append(f"El precio por m² está {abs(discount_pct):.1f}% por encima de la mediana local.")

        # Component B: Gross Rental Yield (0 - 25 points)
        # Benchmark en Colombia: 5.5% - 6.5% es promedio, > 7.5% es muy atractivo
        if gross_yield_pct >= 9.0:
            score_yield = 25.0
            reasons.append(f"Rentabilidad bruta excepcional proyectada: {gross_yield_pct:.2f}% anual.")
        elif gross_yield_pct >= 7.5:
            score_yield = 20.0 + (gross_yield_pct - 7.5) * 3.3
            reasons.append(f"Rentabilidad bruta superior a la media colombiana: {gross_yield_pct:.2f}%.")
        elif gross_yield_pct >= 6.0:
            score_yield = 14.0 + (gross_yield_pct - 6.0) * 4.0
        else:
            score_yield = max(0.0, gross_yield_pct * 2.0)
            risks.append(f"Rentabilidad proyectada moderada ({gross_yield_pct:.2f}% bruto).")

        # Component C: Days on Market / Alert Speed (0 - 15 points)
        if prop.days_on_market <= 5:
            score_timing = 15.0
            reasons.append("Oferta recién publicada (menos de 5 días en portal). Ventaja de primer comprador.")
        elif prop.days_on_market <= 15:
            score_timing = 12.0
        elif prop.days_on_market <= 45:
            score_timing = 8.0
        elif prop.days_on_market > 90:
            score_timing = 10.0
            reasons.append("Lleva más de 90 días en el mercado: Alto margen de negociación agresiva.")
        else:
            score_timing = 6.0

        # Component D: Administration Fee Ratio (0 - 10 points)
        monthly_admin_ratio = (prop.admin_fee_cop / prop.price_cop) if prop.price_cop > 0 else 0
        if prop.admin_fee_cop == 0:
            score_admin = 7.0  # Posible casa o cuota no reportada
        elif monthly_admin_ratio <= 0.0008:
            score_admin = 10.0
            reasons.append("Administración económica que no castiga el flujo de caja mensual.")
        elif monthly_admin_ratio <= 0.0014:
            score_admin = 7.0
        else:
            score_admin = 2.0
            risks.append(f"Cuota de administración elevada (${prop.admin_fee_cop:,.0f} COP/mes), afecta el yield neto.")

        # Component E: Physical Attributes & Added Value (0 - 10 points)
        score_amenities = 0.0
        if prop.parking_spots >= 1:
            score_amenities += 4.0
            reasons.append(f"Cuenta con {prop.parking_spots} parqueadero(s) asignado(s), activo de alta liquidez.")
        if prop.has_balcony or prop.has_storage_room:
            score_amenities += 3.0
        if prop.has_elevator or (prop.floor_number and prop.floor_number <= 3):
            score_amenities += 3.0

        total_score = min(100.0, round(score_discount + score_yield + score_timing + score_admin + score_amenities, 1))

        # Determine Strategy
        tourist_zones = ["poblado", "laureles", "bocagrande", "chapinero", "castillogrande", "parque 93"]
        is_tourist_zone = any(z in prop.location.neighborhood.lower() for z in tourist_zones)

        if discount_pct >= 20.0 and (prop.property_age_years or 0) >= 15:
            strategy = InvestmentStrategy.FLIPPING
            reasons.append("Estrategia recomendada: Flipping inmobiliario (Remodelar acabados antiguos y revender a valor de mercado).")
        elif is_tourist_zone and gross_yield_pct >= 7.5:
            strategy = InvestmentStrategy.SHORT_TERM_RENTAL
            reasons.append("Estrategia recomendada: Renta Corta / Airbnb (Zona de alta demanda turística o ejecutiva).")
        else:
            strategy = InvestmentStrategy.LONG_TERM_RENTAL
            reasons.append("Estrategia recomendada: Renta Tradicional o Vivienda Propia (Flujo de caja predecible).")

        return OpportunityAnalysis(
            property_id=prop.id,
            opportunity_score=total_score,
            discount_vs_neighborhood_pct=round(discount_pct, 1),
            benchmark_price_m2=round(benchmark_price_m2, 0),
            actual_price_m2=round(actual_price_m2, 0),
            estimated_fair_market_value_cop=round(fair_market_value_cop, 0),
            gross_annual_rental_yield_pct=round(gross_yield_pct, 2),
            estimated_monthly_rent_cop=round(estimated_monthly_rent_cop, 0),
            net_annual_yield_pct=round(net_yield_pct, 2),
            recommended_strategy=strategy,
            score_reasons=reasons,
            risk_factors=risks,
            confidence_level=confidence
        )
