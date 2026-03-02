from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models import ApiProfile, SavedAnalysis, User
from app.schemas.persistence import (
    ApiProfileCreate,
    ApiProfileResponse,
    ResourceDeleteResponse,
    SavedAnalysisCreate,
    SavedAnalysisResponse,
)

router = APIRouter()


@router.get("/api-profiles", response_model=list[ApiProfileResponse])
def list_api_profiles(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ApiProfileResponse]:
    rows = db.scalars(select(ApiProfile).where(ApiProfile.user_id == user.id).order_by(ApiProfile.created_at.desc())).all()
    return [ApiProfileResponse(id=row.id, name=row.name, provider_keys=row.provider_keys) for row in rows]


@router.post("/api-profiles", response_model=ApiProfileResponse)
def create_api_profile(
    payload: ApiProfileCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiProfileResponse:
    row = ApiProfile(id=payload.id, user_id=user.id, name=payload.name, provider_keys=payload.provider_keys)
    db.merge(row)
    db.commit()
    return ApiProfileResponse(id=row.id, name=row.name, provider_keys=row.provider_keys)


@router.put("/api-profiles/{profile_id}", response_model=ApiProfileResponse)
def update_api_profile(
    profile_id: str,
    payload: ApiProfileCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiProfileResponse:
    row = db.get(ApiProfile, profile_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="API profile not found.")
    row.name = payload.name
    row.provider_keys = payload.provider_keys
    db.add(row)
    db.commit()
    db.refresh(row)
    return ApiProfileResponse(id=row.id, name=row.name, provider_keys=row.provider_keys)


@router.delete("/api-profiles/{profile_id}", response_model=ResourceDeleteResponse)
def delete_api_profile(
    profile_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResourceDeleteResponse:
    row = db.get(ApiProfile, profile_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="API profile not found.")
    db.delete(row)
    db.commit()
    return ResourceDeleteResponse(id=profile_id)


@router.get("/analyses", response_model=list[SavedAnalysisResponse])
def list_saved_analyses(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SavedAnalysisResponse]:
    rows = db.scalars(select(SavedAnalysis).where(SavedAnalysis.user_id == user.id).order_by(SavedAnalysis.created_at.desc())).all()
    return [
        SavedAnalysisResponse(
            id=row.id,
            ticker=row.ticker,
            title=row.title,
            assumptions=row.assumptions,
            output_summary=row.output_summary,
            notes=row.notes,
        )
        for row in rows
    ]


@router.post("/analyses", response_model=SavedAnalysisResponse)
def create_saved_analysis(
    payload: SavedAnalysisCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedAnalysisResponse:
    row = SavedAnalysis(
        id=payload.id,
        user_id=user.id,
        ticker=payload.ticker,
        title=payload.title,
        assumptions=payload.assumptions,
        output_summary=payload.output_summary,
        notes=payload.notes,
    )
    db.merge(row)
    db.commit()
    return SavedAnalysisResponse(
        id=row.id,
        ticker=row.ticker,
        title=row.title,
        assumptions=row.assumptions,
        output_summary=row.output_summary,
        notes=row.notes,
    )


@router.put("/analyses/{analysis_id}", response_model=SavedAnalysisResponse)
def update_saved_analysis(
    analysis_id: str,
    payload: SavedAnalysisCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedAnalysisResponse:
    row = db.get(SavedAnalysis, analysis_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Saved analysis not found.")
    row.ticker = payload.ticker
    row.title = payload.title
    row.assumptions = payload.assumptions
    row.output_summary = payload.output_summary
    row.notes = payload.notes
    db.add(row)
    db.commit()
    db.refresh(row)
    return SavedAnalysisResponse(
        id=row.id,
        ticker=row.ticker,
        title=row.title,
        assumptions=row.assumptions,
        output_summary=row.output_summary,
        notes=row.notes,
    )


@router.delete("/analyses/{analysis_id}", response_model=ResourceDeleteResponse)
def delete_saved_analysis(
    analysis_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResourceDeleteResponse:
    row = db.get(SavedAnalysis, analysis_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Saved analysis not found.")
    db.delete(row)
    db.commit()
    return ResourceDeleteResponse(id=analysis_id)
