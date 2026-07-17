"""ffmpeg/ffprobe wrappers.

Pure subprocess calls — no heavy Python deps. Raises :class:`MediaError` with
useful context on failure.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


class MediaError(Exception):
    """Raised for ffmpeg/ffprobe failures."""


@dataclass
class StreamInfo:
    index: int
    codec_type: str            # "video" | "audio" | "subtitle" | ...
    codec_name: str
    duration: float | None = None


@dataclass
class MediaInfo:
    path: Path
    format_name: str
    duration: float
    streams: list[StreamInfo] = field(default_factory=list)

    @property
    def has_video(self) -> bool:
        return any(s.codec_type == "video" for s in self.streams)

    @property
    def has_audio(self) -> bool:
        return any(s.codec_type == "audio" for s in self.streams)

    @property
    def is_video(self) -> bool:
        # A container with a real video stream (not just cover-art) is video.
        return self.has_video


def _which(name: str) -> str:
    exe = shutil.which(name)
    if not exe:
        raise MediaError(
            f"{name} not found on PATH. Install ffmpeg (which provides {name}) and retry."
        )
    return exe


def ensure_ffmpeg() -> None:
    """Raise if ffmpeg or ffprobe are not available."""
    _which("ffmpeg")
    _which("ffprobe")


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise MediaError(
            f"Command failed (exit {proc.returncode}): {' '.join(cmd)}\n"
            f"{proc.stderr[-2000:]}"
        )
    return proc


def probe(path: Path) -> MediaInfo:
    """Return container/stream info via ffprobe."""
    path = Path(path)
    if not path.exists():
        raise MediaError(f"Input does not exist: {path}")
    ffprobe = _which("ffprobe")
    proc = _run(
        [
            ffprobe, "-v", "error", "-show_format", "-show_streams",
            "-of", "json", str(path),
        ]
    )
    data = json.loads(proc.stdout)
    fmt = data.get("format", {})
    duration = float(fmt.get("duration", 0.0) or 0.0)
    streams: list[StreamInfo] = []
    for s in data.get("streams", []):
        streams.append(
            StreamInfo(
                index=int(s.get("index", 0)),
                codec_type=s.get("codec_type", "unknown"),
                codec_name=s.get("codec_name", "unknown"),
                duration=float(s["duration"]) if s.get("duration") else None,
            )
        )
    return MediaInfo(
        path=path,
        format_name=fmt.get("format_name", "unknown"),
        duration=duration,
        streams=streams,
    )


def extract_audio(
    source: Path, output_wav: Path, sample_rate: int = 40_000, channels: int = 1
) -> Path:
    """Extract/normalize the audio track to a canonical mono WAV for the engine."""
    ffmpeg = _which("ffmpeg")
    output_wav = Path(output_wav)
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            ffmpeg, "-y", "-i", str(source),
            "-vn",                       # drop video
            "-ac", str(channels),
            "-ar", str(sample_rate),
            "-c:a", "pcm_s16le",
            str(output_wav),
        ]
    )
    return output_wav


def remux_audio(
    original_video: Path,
    converted_audio: Path,
    output: Path,
    audio_codec: str = "aac",
    audio_bitrate: str = "192k",
) -> Path:
    """Mux converted audio into the original container, copying video/subs verbatim.

    * Video stream is copied bit-identical (``-c:v copy``) — never re-encoded.
    * Subtitle streams are copied.
    * The new audio track replaces the original; output is trimmed to the
      shortest stream so A/V stays in sync.
    """
    ffmpeg = _which("ffmpeg")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            ffmpeg, "-y",
            "-i", str(original_video),     # 0: original (video + subs)
            "-i", str(converted_audio),    # 1: converted audio
            "-map", "0:v",                 # video from original
            "-map", "1:a",                 # audio from converted
            "-map", "0:s?",                # subtitles if present (optional)
            "-c:v", "copy",                # bit-identical video
            "-c:s", "copy",                # copy subtitles
            "-c:a", audio_codec,
            "-b:a", audio_bitrate,
            "-map_metadata", "0",          # preserve container metadata
            "-shortest",
            str(output),
        ]
    )
    return output
