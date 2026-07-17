"""VoiceMorph engine — voice conversion (speech-to-speech) core.

This package provides:

* A stable, backend-agnostic voice-conversion interface
  (:mod:`voicemorph_engine.backends.base`), so the RVC implementation can be
  upgraded or swapped without touching callers.
* A voice-profile registry with a **mandatory consent record**
  (:mod:`voicemorph_engine.profiles`).
* Preprocessing utilities (:mod:`voicemorph_engine.preprocessing`).
* A CLI entry point (``voicemorph``).

Heavy ML dependencies (torch, RVC, faiss) are imported lazily inside the RVC
backend so this package imports on any interpreter without them installed.
"""

from __future__ import annotations

__version__ = "0.1.0"

from voicemorph_engine.backends.base import (
    ConversionParams,
    ConversionResult,
    TrainingParams,
    TrainingResult,
    VoiceConversionBackend,
)
from voicemorph_engine.profiles import ConsentRecord, ProfileRegistry, VoiceProfile

__all__ = [
    "__version__",
    "ConversionParams",
    "ConversionResult",
    "TrainingParams",
    "TrainingResult",
    "VoiceConversionBackend",
    "ConsentRecord",
    "ProfileRegistry",
    "VoiceProfile",
]
