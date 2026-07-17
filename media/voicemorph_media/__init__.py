"""VoiceMorph media I/O layer.

A thin, well-tested wrapper over ``ffmpeg``/``ffprobe`` that:

* detects whether an input is audio-only or video,
* extracts the audio track to a canonical WAV for the engine,
* remuxes converted audio back into the *original* container while copying the
  video stream bit-identically (``-c:v copy``) and preserving subtitle/metadata
  streams,
* guards that output duration matches input within tolerance.

The engine depends on :func:`voicemorph_media.pipeline.convert_media` to route
audio-vs-video without knowing anything about containers.
"""

from __future__ import annotations

__version__ = "0.1.0"

from voicemorph_media.ffmpeg import (
    MediaInfo,
    StreamInfo,
    ensure_ffmpeg,
    extract_audio,
    probe,
    remux_audio,
)

__all__ = [
    "__version__",
    "MediaInfo",
    "StreamInfo",
    "ensure_ffmpeg",
    "extract_audio",
    "probe",
    "remux_audio",
]
