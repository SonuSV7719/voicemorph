"""Backend-agnostic voice-conversion interface.

Every backend (RVC today, others later) implements
:class:`VoiceConversionBackend`. Callers — the CLI, the backend workers, the
streaming handler — depend only on this interface and the plain data objects
defined here, never on a concrete backend.

Design contract for all backends:

* **Content & timing preservation.** ``convert_file`` must return audio whose
  duration matches the source within :data:`config.DURATION_TOLERANCE_SECONDS`.
  Backends preserve the source F0 contour and timing; only timbre is converted.
* **Idempotent model residency.** ``load_voice`` may be called repeatedly; a
  backend should cache the resident model so streaming sessions never pay a
  per-chunk cold-load cost.
"""

from __future__ import annotations

import abc
from collections.abc import Iterable, Iterator
from pathlib import Path

import numpy as np
from pydantic import BaseModel, Field


class TrainingParams(BaseModel):
    """Parameters for training a per-target-voice model."""

    epochs: int = 200
    batch_size: int = 8
    sample_rate: int = 40_000
    # RMVPE is the default/best-practice pitch estimator for RVC pipelines.
    pitch_method: str = "rmvpe"
    # Build the retrieval (.index) file for timbre retrieval blending.
    build_index: bool = True
    seed: int = 1234


class TrainingResult(BaseModel):
    voice_id: str
    model_path: str
    index_path: str | None = None
    epochs_trained: int
    sample_rate: int
    metrics: dict = Field(default_factory=dict)


class ConversionParams(BaseModel):
    """Parameters for a single conversion (batch or per-stream-session)."""

    # Semitone transpose. 0 keeps the *original speaker's* pitch register, which
    # is what we want for faithful delivery preservation; expose for edge cases
    # (e.g. large source/target register gaps).
    transpose: int = 0
    pitch_method: str = "rmvpe"
    # Retrieval blend ratio in [0,1]: how strongly to pull timbre toward the
    # trained voice's feature index. Higher = closer timbre, less artifacting.
    index_rate: float = 0.75
    # Protect voiceless consonants/breath from over-conversion (RVC "protect").
    protect: float = 0.33
    # Volume envelope mix: 1.0 = follow source loudness dynamics exactly.
    rms_mix_rate: float = 1.0


class ConversionResult(BaseModel):
    """Result of a batch conversion. Audio is written to ``output_path``."""

    voice_id: str
    output_path: str
    sample_rate: int
    source_duration: float
    output_duration: float
    real_time_factor: float | None = None  # processing_time / audio_duration


class StreamConfig(BaseModel):
    chunk_seconds: float = 0.3
    crossfade_seconds: float = 0.04
    sample_rate: int = 40_000


class VoiceConversionBackend(abc.ABC):
    """Abstract base every VC backend implements."""

    #: short identifier, e.g. "rvc"
    backend_id: str = "base"

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Return True if the backend's ML dependencies and weights are present."""

    @abc.abstractmethod
    def train(
        self,
        voice_id: str,
        dataset_dir: Path,
        output_dir: Path,
        params: TrainingParams,
        progress: ProgressCallback | None = None,
    ) -> TrainingResult:
        """Train a model for ``voice_id`` from preprocessed clips in ``dataset_dir``."""

    @abc.abstractmethod
    def load_voice(self, voice_id: str, model_path: Path, index_path: Path | None) -> None:
        """Load (and cache) a trained voice model into memory/GPU for inference."""

    @abc.abstractmethod
    def convert_file(
        self,
        voice_id: str,
        source_audio: Path,
        output_path: Path,
        params: ConversionParams,
    ) -> ConversionResult:
        """Batch-convert ``source_audio`` to the target voice, preserving duration."""

    @abc.abstractmethod
    def convert_stream(
        self,
        voice_id: str,
        chunks: Iterable[np.ndarray],
        params: ConversionParams,
        stream_config: StreamConfig,
    ) -> Iterator[np.ndarray]:
        """Convert an iterable of float32 mono audio chunks, yielding converted chunks.

        The model must remain resident across the session; crossfade is applied
        at chunk boundaries to hide seams.
        """

    def unload_voice(self, voice_id: str) -> None:  # noqa: B027 - optional hook, default no-op
        """Optional: release a resident voice model. Default is a no-op."""


class ProgressCallback:
    """Minimal progress sink for long-running training/conversion.

    Callers pass an instance; backends call it with ``(fraction, message)``.
    """

    def __call__(self, fraction: float, message: str) -> None:  # pragma: no cover
        pass
