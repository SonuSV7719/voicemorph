"""RVC (Retrieval-based Voice Conversion) backend.

Wraps the RVC-Project inference/training stack behind
:class:`VoiceConversionBackend`. All heavy imports (torch, rvc-python, librosa,
faiss) happen lazily inside methods so importing this module never requires the
``[ml]`` extra to be installed.

Duration preservation
----------------------
RVC converts frame-synchronously and keeps the source F0 contour, so the output
is inherently the same length as the input. ``convert_file`` additionally
verifies this and raises :class:`DurationMismatchError` if drift exceeds the
tolerance — content/timing preservation is a hard requirement, not a hope.

Model residency
---------------
``load_voice`` caches the loaded inference session per ``voice_id`` in
``self._resident`` so streaming sessions and repeated batch jobs never pay a
cold-load cost.
"""

from __future__ import annotations

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
from voicemorph_engine.config import DURATION_TOLERANCE_SECONDS, EngineConfig
from voicemorph_engine.errors import (
    BackendUnavailableError,
    DurationMismatchError,
    ProfileNotTrainedError,
)


class RVCBackend(VoiceConversionBackend):
    backend_id = "rvc"

    def __init__(self, config: EngineConfig):
        self.config = config
        # voice_id -> loaded inference session object (backend-specific)
        self._resident: dict[str, object] = {}
        self._device: str | None = None

    # -- capability / device ------------------------------------------------

    def is_available(self) -> bool:
        """True if the ML stack imports. Weight presence is checked at train time."""
        try:
            import rvc_python  # noqa: F401
            import torch  # noqa: F401
        except Exception:
            return False
        return True

    def _resolve_device(self) -> str:
        if self._device is not None:
            return self._device
        if self.config.device != "auto":
            self._device = self.config.device
            return self._device
        try:
            import torch

            self._device = "cuda:0" if torch.cuda.is_available() else "cpu"
        except Exception:
            self._device = "cpu"
        return self._device

    def _require_ml(self):
        if not self.is_available():
            raise BackendUnavailableError(
                "RVC backend unavailable. Install the ML extra in a Python 3.10/3.11 "
                'environment: pip install "voicemorph-engine[ml]", and ensure the RMVPE '
                "and pretrained base weights are present under the models directory. "
                "See docs/ENGINE.md."
            )

    # -- training -----------------------------------------------------------

    def train(
        self,
        voice_id: str,
        dataset_dir: Path,
        output_dir: Path,
        params: TrainingParams,
        progress: ProgressCallback | None = None,
    ) -> TrainingResult:
        """Train a per-voice ``.pth`` model (+ ``.index``) from preprocessed clips.

        ``dataset_dir`` must already contain sliced, canonical-rate mono WAV
        clips (see :mod:`voicemorph_engine.preprocessing`). This method drives
        the RVC training pipeline: feature extraction → F0 (RMVPE) extraction →
        model training → retrieval index build.
        """
        self._require_ml()
        output_dir.mkdir(parents=True, exist_ok=True)
        device = self._resolve_device()

        # --- RVC training driver -------------------------------------------
        # Implemented against the RVC-Project training pipeline. Kept isolated
        # in a helper so the exact third-party call surface lives in one place.
        from voicemorph_engine.backends._rvc_driver import run_training

        model_path, index_path, metrics = run_training(
            dataset_dir=dataset_dir,
            output_dir=output_dir,
            voice_id=voice_id,
            device=device,
            pretrained_dir=self.config.pretrained_dir,
            rmvpe_dir=self.config.rmvpe_dir,
            params=params,
            progress=progress,
        )

        return TrainingResult(
            voice_id=voice_id,
            model_path=str(model_path),
            index_path=str(index_path) if index_path else None,
            epochs_trained=params.epochs,
            sample_rate=params.sample_rate,
            metrics=metrics,
        )

    # -- inference: batch ---------------------------------------------------

    def load_voice(
        self, voice_id: str, model_path: Path, index_path: Path | None
    ) -> None:
        self._require_ml()
        if voice_id in self._resident:
            return
        from voicemorph_engine.backends._rvc_driver import load_inference_session

        self._resident[voice_id] = load_inference_session(
            model_path=model_path,
            index_path=index_path,
            device=self._resolve_device(),
            rmvpe_dir=self.config.rmvpe_dir,
        )

    def convert_file(
        self,
        voice_id: str,
        source_audio: Path,
        output_path: Path,
        params: ConversionParams,
    ) -> ConversionResult:
        self._require_ml()
        if voice_id not in self._resident:
            raise ProfileNotTrainedError(
                f"Voice {voice_id!r} is not loaded. Call load_voice() first."
            )
        session = self._resident[voice_id]
        output_path.parent.mkdir(parents=True, exist_ok=True)

        source_info = sf.info(str(source_audio))
        source_duration = source_info.frames / source_info.samplerate

        from voicemorph_engine.backends._rvc_driver import infer_file

        sample_rate, rtf = infer_file(
            session=session,
            source_audio=source_audio,
            output_path=output_path,
            params=params,
        )

        out_info = sf.info(str(output_path))
        output_duration = out_info.frames / out_info.samplerate

        drift = abs(output_duration - source_duration)
        if drift > DURATION_TOLERANCE_SECONDS:
            raise DurationMismatchError(
                f"Output duration {output_duration:.3f}s drifted {drift:.3f}s from "
                f"source {source_duration:.3f}s (tolerance {DURATION_TOLERANCE_SECONDS}s). "
                "Conversion must preserve timing exactly."
            )

        return ConversionResult(
            voice_id=voice_id,
            output_path=str(output_path),
            sample_rate=sample_rate,
            source_duration=source_duration,
            output_duration=output_duration,
            real_time_factor=rtf,
        )

    # -- inference: streaming ----------------------------------------------

    def convert_stream(
        self,
        voice_id: str,
        chunks: Iterable[np.ndarray],
        params: ConversionParams,
        stream_config: StreamConfig,
    ) -> Iterator[np.ndarray]:
        self._require_ml()
        if voice_id not in self._resident:
            raise ProfileNotTrainedError(
                f"Voice {voice_id!r} is not loaded. Call load_voice() first."
            )
        session = self._resident[voice_id]
        from voicemorph_engine.backends._rvc_driver import StreamingConverter

        converter = StreamingConverter(session, params, stream_config)
        for chunk in chunks:
            yield converter.process(np.asarray(chunk, dtype=np.float32))
        tail = converter.flush()
        if tail is not None and len(tail):
            yield tail

    def unload_voice(self, voice_id: str) -> None:
        self._resident.pop(voice_id, None)
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
