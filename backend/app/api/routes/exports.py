from __future__ import annotations

import base64

from fastapi import APIRouter, HTTPException

from app.schemas.company import AnalysisRequest, ExportResponse
from app.services.analysis_service import build_export_package

router = APIRouter()


@router.post("/workbook", response_model=ExportResponse)
def export_workbook(payload: AnalysisRequest) -> ExportResponse:
    try:
        file_name, content = build_export_package(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ExportResponse(file_name=file_name, content_base64=base64.b64encode(content).decode("utf-8"))
