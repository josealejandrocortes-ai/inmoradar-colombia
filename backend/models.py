"""
Data models and schemas for Colombian Real Estate Radar (InmoRadar Colombia).
Standardized schema handling Colombian market peculiarities:
- Estrato (1-6)
- Administración monthly fee
- Built area vs Private area
- Neighborhood / Localidad
- Identification of duplicate listings cross-portal
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PropertyType(str, Enum):
    APARTMENT = "apartamento"
    HOUSE = "casa"
    STUDIO = "apartaestudio"
    OFFICE = "oficina"
    LOT = "lote"


class PortalSource(str, Enum):
    FINCARAIZ = "fincaraiz"
    METROCUADRADO = "metrocuadrado"
    CIENCUADRAS = "ciencuadras"
    PROPERATI = "properati"
    MERCADOLIBRE = "mercadolibre"
    HABI = "habi"


class InvestmentStrategy(str, Enum):
    FLIPPING = "flipping_remodelacion"       # Buy low, remodel, resell
    LONG_TERM_RENTAL = "renta_tradicional"    # Stable cashflow, low risk
    SHORT_TERM_RENTAL = "renta_corta_airbnb"  # High yield tourist zones


@dataclass
class ColombianLocation:
    city: str                          # e.g., "Bogotá", "Medellín", "Cali"
    locality: Optional[str] = None     # e.g., "Usaquén", "Chapinero", "Poblado"
    neighborhood: str = ""             # e.g., "Chicó Reservado", "Laureles"
    address_reference: str = ""        # Sanitized / approximate address
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    estrato: int = 4                   # 1 to 6 (Crucial for Colombian property taxes & utilities)


@dataclass
class PropertyListing:
    id: str                            # Unique internal hash
    portal: PortalSource
    external_id: str                   # ID in source portal
    url: str
    title: str
    property_type: PropertyType
    location: ColombianLocation
    price_cop: float                   # Sale price in Colombian Pesos
    built_area_m2: float               # Área construida
    private_area_m2: Optional[float] = None  # Área privada
    bedrooms: int = 1
    bathrooms: int = 1
    parking_spots: int = 0
    stratum: int = 4                   # Estrato socioeconómico (1-6)
    admin_fee_cop: float = 0.0         # Cuota de administración mensual
    property_age_years: Optional[int] = None
    floor_number: Optional[int] = None
    has_elevator: bool = False
    has_balcony: bool = False
    has_storage_room: bool = False     # Depósito / Cuarto útil
    images: List[str] = field(default_factory=list)
    description: str = ""
    listing_date: Optional[str] = None
    days_on_market: int = 0
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def price_per_m2(self) -> float:
        area = self.built_area_m2 or self.private_area_m2 or 1.0
        return self.price_cop / area

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["price_per_m2"] = self.price_per_m2
        return data


@dataclass
class MarketBenchmark:
    city: str
    neighborhood: str
    estrato: int
    property_type: PropertyType
    avg_price_m2: float
    median_price_m2: float
    min_price_m2: float
    max_price_m2: float
    estimated_monthly_rent_m2: float   # Estimated rental income per m2
    total_samples: int
    updated_at: str


@dataclass
class OpportunityAnalysis:
    property_id: str
    opportunity_score: float           # 0.0 to 100.0 score
    discount_vs_neighborhood_pct: float  # e.g., +22.5% below market
    benchmark_price_m2: float
    actual_price_m2: float
    estimated_fair_market_value_cop: float
    gross_annual_rental_yield_pct: float # (Annual Rent / Purchase Price) * 100
    estimated_monthly_rent_cop: float
    net_annual_yield_pct: float         # Accounting for admin fee, property tax (predial), vacancy
    recommended_strategy: InvestmentStrategy
    score_reasons: List[str]
    risk_factors: List[str]
    confidence_level: str              # "Alta", "Media", "Baja" (based on sample density)
