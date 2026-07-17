"""Passthrough (identity) backend — for development, CI, and pipeline tests.

Performs **no voice conversion**: it copies the source audio through unchanged
while honoring the same interface and duration-preservation contract as a real
backend. This lets the whole system (media routing, backend API, job queue,
streaming) be exercised end-to-end on CPU without the ML stack or a GPU.

Never use this as a real conversion backend — it does not change the voice.
"""

from __future__ import annotations

import json
import shutil
import time
from collections.abc import Iterable, Iterator
from pathlib import Path

import numpy as np
import soundfile as sf

from voicemorph_engine.backends.base import (
    ConversionParams,
    ConversionResult,
    ProgressCallback,
    StreamConfig,
    TrainingParams,
    TrainingResult,
    VoiceConversionBackend,
)
from voicemorph_engine.config import EngineConfig


class PassthroughBackend(VoiceConversionBackend):
    backend_id = "passthrough"

    def __init__(self, config: EngineConfig):
        self.config = config
        self._loaded: set[str] = set()

    def is_available(self) -> bool:
        return True

    def train(
        self,
        voice_id: str,
        dataset_dir: Path,
        output_dir: Path,
        params: TrainingParams,
        progress: ProgressCallback | None = None,
    ) -> TrainingResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        model_path = output_dir / "model.pth"
        # Write a tiny marker "model" so downstream status/plumbing is realistic.
        model_path.write_text(
            json.dumps({"backend": "passthrough", "voice_id": voice_id}), encoding="utf-8"
        )
        if progress:
            progress(1.0, "passthrough training complete (identity)")
        return TrainingResult(
            voice_id=voice_id,
            model_path=str(model_path),
            index_path=None,
            epochs_trained=params.epochs,
            sample_rate=params.sample_rate,
            metrics={"note": "identity backend; no conversion performed"},
        )

    def load_voice(self, voice_id: str, model_path: Path, index_path: Path | None) -> None:
        self._loaded.add(voice_id)

    def convert_file(
        self,
        voice_id: str,
        source_audio: Path,
        output_path: Path,
        params: ConversionParams,
    ) -> ConversionResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        info = sf.info(str(source_audio))
        duration = info.frames / info.samplerate
        t0 = time.perf_counter()
        shutil.copyfile(source_audio, output_path)
        elapsed = time.perf_counter() - t0
        return ConversionResult(
            voice_id=voice_id,
            output_path=str(output_path),
            sample_rate=info.samplerate,
            source_duration=duration,
            output_duration=duration,
            real_time_factor=(elapsed / duration) if duration else None,
        )

    def convert_stream(
        self,
        voice_id: str,
        chunks: Iterable[np.ndarray],
        params: ConversionParams,
        stream_config: StreamConfig,
    ) -> Iterator[np.ndarray]:
        for chunk in chunks:
            yield np.asarray(chunk, dtype=np.float32)

    def unload_voice(self, voice_id: str) -> None:
        self._loaded.discard(voice_id)
