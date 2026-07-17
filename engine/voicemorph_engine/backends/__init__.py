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

    Kept as a small factory so alternative backends (e.g. a future so-vits-svc
    or seed-vc backend) can be registered without changing call sites.
    """
    backend_id = config.backend.lower()
    if backend_id == "rvc":
        from voicemorph_engine.backends.rvc import RVCBackend

        return RVCBackend(config)
    if backend_id == "passthrough":
        # Identity backend for dev/CI/testing — performs no voice conversion.
        from voicemorph_engine.backends.passthrough import PassthroughBackend

        return PassthroughBackend(config)
    raise BackendUnavailableError(f"Unknown backend id: {config.backend!r}")


__all__ = ["VoiceConversionBackend", "get_backend"]
