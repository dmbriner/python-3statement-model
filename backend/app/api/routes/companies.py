from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.company import (
    AnalysisRequest,
    AnalysisResponse,
    CompanySearchResponse,
)
from app.services.analysis_service import analyze_company, search_for_companies

router = APIRouter()


@router.get("/search", response_model=CompanySearchResponse)
def search_companies_endpoint(query: str) -> CompanySearchResponse:
    return CompanySearchResponse(results=search_for_companies(query))


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_company_endpoint(payload: AnalysisRequest) -> AnalysisResponse:
    try:
        return analyze_company(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
