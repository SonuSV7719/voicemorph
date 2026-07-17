"""Typed exceptions for the VoiceMorph engine."""

from __future__ import annotations


class VoiceMorphError(Exception):
    """Base class for all engine errors."""


class ConsentRequiredError(VoiceMorphError):
    """Raised when profile training is attempted without a valid consent record.

    This is a hard guardrail: VoiceMorph will not train a voice profile unless
    the caller supplies an explicit consent record. See docs/ETHICS.md.
    """


class ProfileNotFoundError(VoiceMorphError):
    """Raised when a referenced ``voice_id`` does not exist in the registry."""


class ProfileNotTrainedError(VoiceMorphError):
    """Raised when conversion is requested against an untrained profile."""


class BackendUnavailableError(VoiceMorphError):
    """Raised when the ML backend cannot be initialized (missing deps / GPU)."""


class MediaError(VoiceMorphError):
    """Raised for audio/video I/O problems surfaced to the engine."""


class DurationMismatchError(VoiceMorphError):
    """Raised when converted output duration drifts beyond tolerance.

    Content and timing preservation is a non-negotiable requirement; a duration
    drift signals the conversion violated it.
    """
