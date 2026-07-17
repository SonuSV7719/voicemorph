"""Voice-profile registry with a mandatory consent record.

A :class:`VoiceProfile` is the per-target-voice unit: it points at the trained
model artifacts (``.pth`` + ``.index``) and carries a :class:`ConsentRecord`.
Training is refused unless a consent record is present (see docs/ETHICS.md).

The registry is a simple JSON-per-profile store on disk so it works without any
database in the engine layer; the backend service can layer its own storage on
top of the same schema.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from voicemorph_engine.errors import ConsentRequiredError, ProfileNotFoundError


class ConsentMethod(str, Enum):
    SELF = "self"                    # the user's own voice
    WRITTEN = "written"              # documented written consent
    RECORDED = "recorded"            # recorded verbal consent
    CONTRACT = "contract"            # talent/production contract


class ConsentRecord(BaseModel):
    """Proof-of-consent attached to every trainable voice profile.

    This is a guardrail, not merely metadata: :func:`ConsentRecord.validate_ok`
    is checked before any training run.
    """

    subject: str = Field(..., description="Whose voice this is (name/identifier).")
    granted_by: str = Field(..., description="Who granted consent (may equal subject).")
    method: ConsentMethod = ConsentMethod.SELF
    confirmed: bool = Field(
        default=False,
        description="Caller explicitly confirmed they hold the right to use this voice.",
    )
    reference: str | None = Field(
        default=None, description="Pointer to consent artifact (doc id, file, URL)."
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def validate_ok(self) -> None:
        if not self.confirmed:
            raise ConsentRequiredError(
                "Consent not confirmed. A voice profile may only be trained from your "
                "own voice or a voice you have explicit consent to use. Set "
                "consent.confirmed=True only if that is true. See docs/ETHICS.md."
            )
        if not self.subject.strip() or not self.granted_by.strip():
            raise ConsentRequiredError("Consent record must name the subject and grantor.")


class ProfileStatus(str, Enum):
    CREATED = "created"
    PREPROCESSING = "preprocessing"
    TRAINING = "training"
    READY = "ready"
    FAILED = "failed"


class VoiceProfile(BaseModel):
    voice_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str
    consent: ConsentRecord
    status: ProfileStatus = ProfileStatus.CREATED
    backend: str = "rvc"
    sample_rate: int = 40_000
    # Artifact paths, relative to the profile directory, once trained.
    model_path: str | None = None   # .pth
    index_path: str | None = None   # .index
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = Field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    @property
    def is_ready(self) -> bool:
        return self.status == ProfileStatus.READY and bool(self.model_path)


class ProfileRegistry:
    """JSON-per-profile store rooted at ``profiles_dir``.

    Layout::

        <profiles_dir>/<voice_id>/profile.json
        <profiles_dir>/<voice_id>/model.pth
        <profiles_dir>/<voice_id>/model.index
    """

    def __init__(self, profiles_dir: Path):
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def _dir(self, voice_id: str) -> Path:
        return self.profiles_dir / voice_id

    def _file(self, voice_id: str) -> Path:
        return self._dir(voice_id) / "profile.json"

    def create(self, name: str, consent: ConsentRecord, **kwargs) -> VoiceProfile:
        """Create a new profile. Consent is validated up front."""
        consent.validate_ok()
        profile = VoiceProfile(name=name, consent=consent, **kwargs)
        self._dir(profile.voice_id).mkdir(parents=True, exist_ok=True)
        self.save(profile)
        return profile

    def save(self, profile: VoiceProfile) -> None:
        profile.touch()
        self._dir(profile.voice_id).mkdir(parents=True, exist_ok=True)
        self._file(profile.voice_id).write_text(
            profile.model_dump_json(indent=2), encoding="utf-8"
        )

    def get(self, voice_id: str) -> VoiceProfile:
        path = self._file(voice_id)
        if not path.exists():
            raise ProfileNotFoundError(f"No voice profile with id {voice_id!r}.")
        return VoiceProfile.model_validate_json(path.read_text(encoding="utf-8"))

    def exists(self, voice_id: str) -> bool:
        return self._file(voice_id).exists()

    def list(self) -> list[VoiceProfile]:
        out: list[VoiceProfile] = []
        for d in sorted(self.profiles_dir.iterdir()):
            f = d / "profile.json"
            if f.exists():
                out.append(VoiceProfile.model_validate_json(f.read_text(encoding="utf-8")))
        return out

    def delete(self, voice_id: str) -> None:
        import shutil

        d = self._dir(voice_id)
        if not d.exists():
            raise ProfileNotFoundError(f"No voice profile with id {voice_id!r}.")
        shutil.rmtree(d)

    def profile_dir(self, voice_id: str) -> Path:
        return self._dir(voice_id)
