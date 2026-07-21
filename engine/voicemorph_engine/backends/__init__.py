"""Voice-conversion backends.

The engine talks to backends only through the abstract interface in
:mod:`voicemorph_engine.backends.base`. Use :func:`get_backend` to resolve a
backend by id; heavy backends import their ML dependencies lazily so importing
this package never requires torch/RVC to be installed.
"""

from __future__ import annotations

from voicemorph_engine.backends.base import VoiceConversionBackend
from voicemorph_engine.config import EngineConfig
from voicemorph_engine.errors import BackendUnavailableError


def get_backend(config: EngineConfig) -> VoiceConversionBackend:
    """Resolve and instantiate the configured backend.

    ``config.backend == "auto"`` selects the best installed backend for the
    detected hardware (GPU→rvc, else a fast CPU backend); any other value is an
    explicit manual override. Kept as a small factory so alternative backends
    can be registered without changing call sites.
    """
    backend_id = config.backend.lower()
    if backend_id == "auto":
        from voicemorph_engine.hardware import detect_device, recommend_backend

        backend_id = recommend_backend(detect_device(config.device))
    if backend_id == "rvc":
        from voicemorph_engine.backends.rvc import RVCBackend

        return RVCBackend(config)
    if backend_id == "passthrough":
        # Identity backend for dev/CI/testing — performs no voice conversion.
        from voicemorph_engine.backends.passthrough import PassthroughBackend

        return PassthroughBackend(config)
    if backend_id == "speecht5":
        # Zero-shot CPU voice conversion (Microsoft SpeechT5-VC). No training.
        from voicemorph_engine.backends.speecht5 import SpeechT5Backend

        return SpeechT5Backend(config)
    raise BackendUnavailableError(f"Unknown backend id: {config.backend!r}")


__all__ = ["VoiceConversionBackend", "get_backend"]
