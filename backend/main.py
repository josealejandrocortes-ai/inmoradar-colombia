"""
FastAPI Application for InmoRadar Colombia.
Serves REST API endpoints for real estate valuation and hosts the frontend dashboard.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.models import PropertyListing, ColombianLocation, PropertyType, PortalSource
from backend.opportunity_engine import OpportunityEngine
from backend.deduplication import DeduplicationEngine
from backend.scrapers.scanner_service import ScannerService

app = FastAPI(
    title="InmoRadar Colombia API",
    description="Motor de análisis y radar de oportunidades inmobiliarias en Colombia",
    version="1.0.0"
)

# Enable CORS for cloud deployment (allows frontend hosted on GitHub Pages or custom domains)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
ROOT_DIR = Path(__file__).parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
DATA_DIR = ROOT_DIR / "data"

# Initialize valuation engine & scanner
engine = OpportunityEngine(str(DATA_DIR / "colombia_market_benchmarks.json"))
scanner = ScannerService(DATA_DIR)


def load_sample_listings() -> List[Dict[str, Any]]:
    path = DATA_DIR / "sample_opportunities.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# Request Schemas
class CustomAnalysisRequest(BaseModel):
    title: str = Field(..., example="Apartamento en Chicó Reservado")
    city: str = Field(..., example="Bogotá")
    neighborhood: str = Field(..., example="Chicó")
    estrato: int = Field(..., ge=1, le=6, example=6)
    price_cop: float = Field(..., gt=0, example=650000000)
    built_area_m2: float = Field(..., gt=0, example=95)
    bedrooms: int = Field(2, example=3)
    bathrooms: int = Field(2, example=2)
    parking_spots: int = Field(1, example=2)
    admin_fee_cop: float = Field(0, example=520000)
    property_age_years: Optional[int] = Field(None, example=15)
    days_on_market: int = Field(5, example=4)


class FinancialSimulationRequest(BaseModel):
    price_cop: float = Field(..., example=450000000)
    downpayment_pct: float = Field(0.30, example=0.30)
    rate_ea_pct: float = Field(11.8, example=11.8)
    years: int = Field(20, example=20)
    estimated_monthly_rent_cop: float = Field(..., example=2800000)
    admin_fee_cop: float = Field(0, example=300000)


# API Endpoints
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "platform": "InmoRadar Colombia",
        "benchmarks_loaded": len(engine.benchmarks),
        "version": "1.0.0"
    }


@app.get("/api/benchmarks")
def get_benchmarks():
    return engine.benchmarks


@app.get("/api/opportunities")
def get_opportunities(
    city: Optional[str] = Query(None, description="Filtrar por ciudad (ej. Bogotá, Medellín)"),
    estrato: Optional[int] = Query(None, description="Filtrar por estrato (1 a 6)"),
    strategy: Optional[str] = Query(None, description="Flipping, Renta Corta, Renta Tradicional"),
    max_price: Optional[float] = Query(None, description="Precio máximo en COP"),
    sort_by: str = Query("score", description="score, discount, yield, price_asc")
):
    items = load_sample_listings()

    # Apply filters
    filtered = []
    for item in items:
        if city and city.upper() != "ALL" and item["city"].lower() != city.lower():
            continue
        if estrato and item["estrato"] != estrato:
            continue
        if strategy and strategy.upper() != "ALL":
            strat_val = item.get("analysis", {}).get("recommended_strategy", "").lower()
            if strategy.lower() not in strat_val:
                continue
        if max_price and item["price_cop"] > max_price:
            continue
        filtered.append(item)

    # Sort
    if sort_by == "score":
        filtered.sort(key=lambda x: x.get("analysis", {}).get("opportunity_score", 0), reverse=True)
    elif sort_by == "discount":
        filtered.sort(key=lambda x: x.get("analysis", {}).get("discount_vs_neighborhood_pct", 0), reverse=True)
    elif sort_by == "yield":
        filtered.sort(key=lambda x: x.get("analysis", {}).get("gross_annual_rental_yield_pct", 0), reverse=True)
    elif sort_by == "price_asc":
        filtered.sort(key=lambda x: x["price_cop"])

    return {
        "total": len(filtered),
        "opportunities": filtered
    }


@app.post("/api/analyze-custom")
def analyze_custom_property(req: CustomAnalysisRequest):
    prop = PropertyListing(
        id="custom_analysis",
        portal=PortalSource.FINCARAIZ,
        external_id="custom",
        url="",
        title=req.title,
        property_type=PropertyType.APARTMENT,
        location=ColombianLocation(
            city=req.city,
            neighborhood=req.neighborhood,
            estrato=req.estrato
        ),
        price_cop=req.price_cop,
        built_area_m2=req.built_area_m2,
        bedrooms=req.bedrooms,
        bathrooms=req.bathrooms,
        parking_spots=req.parking_spots,
        stratum=req.estrato,
        admin_fee_cop=req.admin_fee_cop,
        property_age_years=req.property_age_years,
        days_on_market=req.days_on_market
    )

    analysis = engine.analyze_property(prop)
    return {
        "property": prop.to_dict(),
        "analysis": analysis.__dict__
    }


@app.post("/api/financial-simulation")
def simulate_mortgage_and_costs(req: FinancialSimulationRequest):
    downpayment = req.price_cop * req.downpayment_pct
    loan_amount = req.price_cop - downpayment

    # Gastos notariales y de registro en Colombia:
    # 0.54% notaría + 1.67% boleta fiscal y registro + ~0.5% retención = ~2.71%
    closing_costs = req.price_cop * 0.0271

    # Tasa mensual a partir de la E.A.
    rate_monthly = ((1.0 + (req.rate_ea_pct / 100.0)) ** (1.0 / 12.0)) - 1.0
    total_months = req.years * 12

    monthly_debt = 0.0
    if loan_amount > 0 and rate_monthly > 0:
        factor = (1.0 + rate_monthly) ** total_months
        monthly_debt = loan_amount * (rate_monthly * factor) / (factor - 1.0)

    # Flujo de caja neto mensual
    monthly_cashflow = req.estimated_monthly_rent_cop - monthly_debt - req.admin_fee_cop
    gross_yield = (req.estimated_monthly_rent_cop * 12.0 / req.price_cop) * 100.0 if req.price_cop > 0 else 0

    return {
        "price_cop": req.price_cop,
        "downpayment_cop": round(downpayment, 0),
        "loan_amount_cop": round(loan_amount, 0),
        "closing_costs_cop": round(closing_costs, 0),
        "total_initial_cash_required": round(downpayment + closing_costs, 0),
        "monthly_debt_cop": round(monthly_debt, 0),
        "monthly_cashflow_cop": round(monthly_cashflow, 0),
        "gross_annual_yield_pct": round(gross_yield, 2)
    }


# Scraping & Ingestion Trigger
@app.post("/api/scrapers/scan")
def trigger_market_scan():
    """
    Triggers a live market scan across Colombian portals, evaluates findings,
    deduplicates against existing data and persists fresh opportunities.
    """
    result = scanner.run_full_scan()
    return result


@app.get("/api/scrapers/status")
def get_scraper_status():
    items = load_sample_listings()
    return {
        "status": "idle",
        "active_opportunities": len(items),
        "supported_portals": ["Finca Raíz", "Metrocuadrado", "Ciencuadras", "Properati"],
        "target_cities": ["Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena"]
    }


# Serve Frontend Dashboard
@app.get("/")
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        index_file = ROOT_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html no encontrado")
    return FileResponse(
        index_file,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

# Mount remaining static files if needed
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
