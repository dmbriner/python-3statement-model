from __future__ import annotations

from pydantic import BaseModel, Field


class ApiProfileCreate(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=120)
    provider_keys: dict


class ApiProfileResponse(BaseModel):
    id: str
    name: str
    provider_keys: dict


class SavedAnalysisCreate(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    ticker: str = Field(min_length=1, max_length=24)
    title: str = Field(min_length=1, max_length=160)
    assumptions: dict
    output_summary: dict
    notes: str | None = None


class SavedAnalysisResponse(BaseModel):
    id: str
    ticker: str
    title: str
    assumptions: dict
    output_summary: dict
    notes: str | None = None


class ResourceDeleteResponse(BaseModel):
    id: str
    deleted: bool = True
