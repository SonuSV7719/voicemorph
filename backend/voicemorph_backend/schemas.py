"""API request/response schemas."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ConsentIn(BaseModel):
    subject: str = Field(..., description="Whose voice this is.")
    granted_by: str | None = Field(None, description="Who granted consent (defaults to subject).")
    method: str = "self"
    reference: str | None = None
    confirmed: bool = Field(
        ...,
        description="MUST be true and truthful: you hold the right to use this voice.",
    )


class VoiceCreatedOut(BaseModel):
    voice_id: str
    name: str
    status: str


class VoiceStatusOut(BaseModel):
    voice_id: str
    name: str
    status: str
    ready: bool
    error: str | None = None
    dataset_seconds: float | None = None


class JobKind(str, Enum):
    TRAIN = "train"
    CONVERT = "convert"


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobOut(BaseModel):
    job_id: str
    kind: JobKind
    state: JobState
    progress: float = 0.0
    message: str | None = None
    voice_id: str | None = None
    result_key: str | None = None      # storage key of the output artifact
    output_kind: str | None = None     # "audio" | "video"
    error: str | None = None
