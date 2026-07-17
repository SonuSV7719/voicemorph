"""RVC-Project integration layer.

This is the *only* module that touches the concrete RVC library. Keeping the
third-party call surface in one place means upgrading RVC, or swapping the
inference package, changes exactly one file.

Two dependency realities we handle honestly:

* **Inference** is provided by the ``rvc-python`` package (an installable
  wrapper around RVC-Project inference). We drive it through its high-level
  ``RVCInference`` API.
* **Training** is *not* part of ``rvc-python`` — the RVC training pipeline lives
  in the RVC-Project WebUI repo. ``run_training`` therefore drives the training
  toolchain configured via ``VOICEMORPH_RVC_TRAIN_CMD`` (see docs/ENGINE.md). If
  it is not configured, we raise a clear, actionable error rather than silently
  producing nothing.

The streaming crossfade (overlap-add) DSP below is pure NumPy and fully
functional/testable without any ML dependency.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import time
from pathlib import Path

import numpy as np
import soundfile as sf

from voicemorph_engine.backends.base import (
    ConversionParams,
    ProgressCallback,
    StreamConfig,
    TrainingParams,
)
from voicemorph_engine.config import CANONICAL_SAMPLE_RATE
from voicemorph_engine.errors import BackendUnavailableError

# --------------------------------------------------------------------------
# Inference
# --------------------------------------------------------------------------

def load_inference_session(
    model_path: Path,
    index_path: Path | None,
    device: str,
    rmvpe_dir: Path,
):
    """Load an RVC inference session and keep it resident.

    Returns the ``RVCInference`` instance (opaque to callers).
    """
    try:
        from rvc_python.infer import RVCInference
    except Exception as exc:  # pragma: no cover - import guard
        raise BackendUnavailableError(
            "rvc-python is not installed. Install the ML extra: "
            'pip install "voicemorph-engine[ml]".'
        ) from exc

    # RMVPE weights are looked up relative to the RVC install / env; expose ours.
    os.environ.setdefault("RMVPE_ROOT", str(rmvpe_dir))

    rvc = RVCInference(device=device)
    rvc.load_model(str(model_path), index_path=str(index_path) if index_path else "")
    return rvc


def _apply_params(session, params: ConversionParams) -> None:
    """Map VoiceMorph ConversionParams onto the RVC inference session."""
    session.set_params(
        f0up_key=params.transpose,
        f0method=params.pitch_method,
        index_rate=params.index_rate,
        protect=params.protect,
        rms_mix_rate=params.rms_mix_rate,
    )


def infer_file(
    session,
    source_audio: Path,
    output_path: Path,
    params: ConversionParams,
) -> tuple[int, float]:
    """Convert a file with a loaded session. Returns (sample_rate, real_time_factor)."""
    _apply_params(session, params)

    info = sf.info(str(source_audio))
    audio_duration = info.frames / info.samplerate

    t0 = time.perf_counter()
    session.infer_file(str(source_audio), str(output_path))
    elapsed = time.perf_counter() - t0

    out_info = sf.info(str(output_path))
    rtf = (elapsed / audio_duration) if audio_duration > 0 else None
    return out_info.samplerate, rtf


# --------------------------------------------------------------------------
# Training (drives the RVC-Project training toolchain)
# --------------------------------------------------------------------------

def run_training(
    dataset_dir: Path,
    output_dir: Path,
    voice_id: str,
    device: str,
    pretrained_dir: Path,
    rmvpe_dir: Path,
    params: TrainingParams,
    progress: ProgressCallback | None = None,
) -> tuple[Path, Path | None, dict]:
    """Train an RVC model, returning (model_path, index_path, metrics).

    The RVC training pipeline (feature extraction → F0 with RMVPE → train →
    index build) is invoked via a configured command template. Configure it
    with the ``VOICEMORPH_RVC_TRAIN_CMD`` environment variable, using the
    placeholders ``{dataset}``, ``{output}``, ``{voice_id}``, ``{device}``,
    ``{epochs}``, ``{batch_size}``, ``{sr}``, ``{pitch}``.

    Example (RVC-Project WebUI training entrypoint)::

        export VOICEMORPH_RVC_TRAIN_CMD='python infer-web.py --train \
            --exp {voice_id} --dataset {dataset} --sr {sr} --f0method {pitch} \
            --epochs {epochs} --batch {batch_size} --device {device} \
            --outdir {output}'
    """
    cmd_template = os.environ.get("VOICEMORPH_RVC_TRAIN_CMD")
    if not cmd_template:
        raise BackendUnavailableError(
            "RVC training toolchain not configured. Set VOICEMORPH_RVC_TRAIN_CMD to the "
            "RVC-Project training command template (see docs/ENGINE.md). Inference works "
            "via rvc-python, but training requires the RVC training scripts + pretrained "
            "base weights (place them under the models/pretrained directory)."
        )

    if progress:
        progress(0.0, "starting RVC training")

    cmd = cmd_template.format(
        dataset=str(dataset_dir),
        output=str(output_dir),
        voice_id=voice_id,
        device=device,
        epochs=params.epochs,
        batch_size=params.batch_size,
        sr=params.sample_rate,
        pitch=params.pitch_method,
    )

    proc = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
    if proc.returncode != 0:
        raise BackendUnavailableError(
            f"RVC training command failed (exit {proc.returncode}).\n"
            f"stderr tail:\n{proc.stderr[-2000:]}"
        )

    # Discover produced artifacts in the output directory.
    model_path = _find_one(output_dir, "*.pth")
    index_path = _find_one(output_dir, "*.index", required=False)
    if progress:
        progress(1.0, "training complete")

    return model_path, index_path, {"stdout_tail": proc.stdout[-2000:]}


def _find_one(directory: Path, pattern: str, required: bool = True) -> Path | None:
    matches = sorted(directory.rglob(pattern))
    if not matches:
        if required:
            raise BackendUnavailableError(
                f"Training finished but no {pattern} was produced in {directory}."
            )
        return None
    # Prefer the most recently modified artifact.
    return max(matches, key=lambda p: p.stat().st_mtime)


# --------------------------------------------------------------------------
# Streaming: overlap-add crossfade converter (pure NumPy DSP)
# --------------------------------------------------------------------------

class StreamingConverter:
    """Chunked real-time conversion with equal-power seam smoothing.

    Incoming chunks are **contiguous** (each covers the next slice of the
    timeline, no overlap), so the converter is **length-preserving**: every
    input chunk yields an output chunk of the same length, and ``flush`` emits
    nothing. This keeps streaming timing aligned with the source — the same
    non-negotiable requirement as batch.

    To hide the audible click where two independently-converted chunks meet, the
    first ``crossfade`` samples of each chunk are equal-power blended with the
    retained tail of the previous converted chunk. This is a seam *smoother*, not
    a true overlap-add reconstruction (which would require overlapping input
    windows); the low-latency, artifact-minimal streaming path with look-back
    context is built in milestone M5.

    Per-window voice conversion is delegated to :meth:`_convert_window` using the
    resident RVC session.
    """

    def __init__(self, session, params: ConversionParams, stream_config: StreamConfig):
        self.session = session
        self.params = params
        self.cfg = stream_config
        self.sr = stream_config.sample_rate or CANONICAL_SAMPLE_RATE
        self._xfade = max(0, int(self.cfg.crossfade_seconds * self.sr))
        self._prev_tail: np.ndarray | None = None
        # Apply conversion params once for the session (not per window).
        if hasattr(session, "set_params"):
            _apply_params(session, params)
        # Equal-power crossfade ramps.
        if self._xfade > 0:
            t = np.linspace(0.0, 1.0, self._xfade, dtype=np.float32)
            self._fade_in = np.sin(0.5 * np.pi * t)
            self._fade_out = np.cos(0.5 * np.pi * t)
        else:
            self._fade_in = self._fade_out = None

    def process(self, chunk: np.ndarray) -> np.ndarray:
        converted = self._convert_window(chunk).astype(np.float32)
        out = converted.copy()
        if self._xfade > 0 and self._prev_tail is not None and converted.size:
            n = min(self._xfade, converted.size, self._prev_tail.size)
            out[:n] = (
                self._prev_tail[-n:] * self._fade_out[:n]
                + converted[:n] * self._fade_in[:n]
            )
        if self._xfade > 0 and converted.size:
            self._prev_tail = converted[-self._xfade:].copy()
        return out

    def flush(self) -> np.ndarray | None:
        # Length-preserving: nothing is held back, so there is no tail to flush.
        return None

    def _convert_window(self, chunk: np.ndarray) -> np.ndarray:
        """Convert a single audio window to the target voice.

        Delegates to an in-memory session method if the RVC session exposes one;
        otherwise falls back to a temp-file round-trip. Optimized in M5.
        """
        infer_array = getattr(self.session, "infer_array", None)
        if callable(infer_array):
            return np.asarray(infer_array(chunk, self.sr), dtype=np.float32)

        # Fallback: temp-file round-trip (correct, not yet latency-optimized).
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "in.wav"
            dst = Path(td) / "out.wav"
            sf.write(str(src), chunk, self.sr)
            infer_file(self.session, src, dst, self.params)
            data, _ = sf.read(str(dst), dtype="float32")
            return data
