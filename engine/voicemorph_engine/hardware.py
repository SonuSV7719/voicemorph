"""Hardware detection and automatic backend/device selection.

VoiceMorph adapts to the machine it runs on:

* **Device** — ``auto`` picks CUDA if an NVIDIA GPU is available, else CPU.
* **Backend** — ``auto`` picks the best *installed* conversion backend for the
  detected hardware (quality-first, but never one the machine can't run).

Everything is overridable manually — set ``EngineConfig.device`` /
``EngineConfig.backend`` (or the ``VOICEMORPH_DEVICE`` /
``VOICEMORPH_ENGINE_BACKEND`` env vars) to force a specific choice.

Detection is dependency-light: package presence is checked with
``importlib.util.find_spec`` (no heavy import), and CUDA is probed via torch
only if torch is installed.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass

# Backend preference order, highest quality first. `auto` walks this list and
# picks the first *registered* backend whose dependencies are importable on this
# machine. Only backends that `get_backend` can actually build belong here;
# hardware constraints (GPU-only) are applied in `recommend_backend`.
_PREFERENCE = ("rvc", "speecht5", "passthrough")


def _installed(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def has_cuda() -> bool:
    """True if a CUDA-capable GPU is usable (torch installed + device present)."""
    if not _installed("torch"):
        return False
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def gpu_name() -> str | None:
    try:
        import torch

        if torch.cuda.is_available():
            return str(torch.cuda.get_device_name(0))
    except Exception:
        pass
    return None


def detect_device(preference: str = "auto") -> str:
    """Resolve a concrete torch device string.

    ``auto`` → ``cuda:0`` if a GPU is available, otherwise ``cpu``. Any other
    value is treated as an explicit manual override and returned as-is.
    """
    if preference and preference.lower() != "auto":
        return preference
    return "cuda:0" if has_cuda() else "cpu"


def backend_available(backend_id: str) -> bool:
    """Whether a backend's dependencies are importable on this machine."""
    bid = backend_id.lower()
    if bid == "passthrough":
        return True
    if bid == "speecht5":
        return _installed("torch") and _installed("transformers")
    if bid == "freevc":
        # single-pass VITS backend; needs torch + WavLM content features
        return _installed("torch") and _installed("librosa")
    if bid == "seedvc":
        return _installed("torch") and _installed("librosa") and _installed("dac")
    if bid == "rvc":
        return _installed("torch") and _installed("rvc_python")
    return False


def recommend_backend(device: str | None = None) -> str:
    """Pick the best installed backend for the (detected or given) device.

    RVC is only auto-selected on a GPU (its per-voice model is trained there);
    on CPU we prefer fast single-pass backends. Falls back to ``passthrough``
    (identity) so the pipeline always runs, even with nothing installed.
    """
    device = device or detect_device()
    on_gpu = device.startswith("cuda")

    if on_gpu and backend_available("rvc"):
        return "rvc"
    for candidate in _PREFERENCE:
        if candidate == "rvc" and not on_gpu:
            continue  # avoid CPU RVC auto-pick (training is impractical on CPU)
        if backend_available(candidate):
            return candidate
    return "passthrough"


@dataclass
class HardwareInfo:
    device: str
    cuda: bool
    gpu: str | None
    recommended_backend: str
    available_backends: list[str]


def probe(device_preference: str = "auto") -> HardwareInfo:
    """Summarize hardware + the auto choices, for diagnostics / the CLI."""
    device = detect_device(device_preference)
    return HardwareInfo(
        device=device,
        cuda=has_cuda(),
        gpu=gpu_name(),
        recommended_backend=recommend_backend(device),
        available_backends=[b for b in _PREFERENCE if backend_available(b)],
    )
