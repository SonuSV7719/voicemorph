"""Engine configuration and canonical audio constants."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field

# --- Canonical audio format used internally by the engine -------------------
# RVC models are trained at a target sample rate (commonly 40 kHz or 48 kHz).
# Preprocessing normalizes everything to mono at this rate before feature
# extraction. Output is resampled back to the source rate on remux.
CANONICAL_SAMPLE_RATE = 40_000
CANONICAL_CHANNELS = 1

# Real-time streaming defaults (tunable per session).
STREAM_CHUNK_SECONDS = 0.3          # 0.2–0.5 s buffers
STREAM_CROSSFADE_SECONDS = 0.04     # overlap-add crossfade to hide chunk seams
STREAM_TARGET_LATENCY_MS = 300      # end-to-end budget on consumer GPU

# Duration-preservation tolerance for batch conversion (content/timing guard).
DURATION_TOLERANCE_SECONDS = 0.05


def _default_root() -> Path:
    """Root directory for engine-managed data (profiles, models, artifacts)."""
    env = os.environ.get("VOICEMORPH_HOME")
    if env:
        return Path(env)
    return Path.home() / ".voicemorph"


class EngineConfig(BaseModel):
    """Runtime configuration for the engine.

    Paths default under ``$VOICEMORPH_HOME`` (or ``~/.voicemorph``). Device is
    resolved lazily by the backend ("auto" → cuda if available, else cpu).
    """

    root: Path = Field(default_factory=_default_root)
    device: str = Field(default="auto", description="auto | cuda | cuda:N | cpu")
    sample_rate: int = CANONICAL_SAMPLE_RATE
    backend: str = Field(default="rvc", description="voice-conversion backend id")

    @property
    def profiles_dir(self) -> Path:
        return self.root / "profiles"

    @property
    def models_dir(self) -> Path:
        return self.root / "models"

    @property
    def artifacts_dir(self) -> Path:
        return self.root / "artifacts"

    @property
    def pretrained_dir(self) -> Path:
        return self.models_dir / "pretrained"

    @property
    def rmvpe_dir(self) -> Path:
        return self.models_dir / "rmvpe"

    def ensure_dirs(self) -> None:
        for p in (
            self.profiles_dir,
            self.models_dir,
            self.artifacts_dir,
            self.pretrained_dir,
            self.rmvpe_dir,
        ):
            p.mkdir(parents=True, exist_ok=True)
