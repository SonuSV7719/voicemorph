"""Media routing: audio-in→audio-out, video-in→video-out.

The engine hands us a ``convert_audio`` callable that maps a source WAV to a
converted WAV. We take care of everything container-related.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from voicemorph_media.ffmpeg import (
    MediaError,
    ensure_ffmpeg,
    extract_audio,
    probe,
    remux_audio,
)

# A callable: (source_wav, output_wav) -> anything. Runs the voice conversion.
ConvertAudioFn = Callable[[Path, Path], object]

DURATION_TOLERANCE_SECONDS = 0.1  # container-level tolerance (looser than engine)


@dataclass
class MediaResult:
    kind: str          # "audio" | "video"
    output: Path
    duration: float


def convert_media(
    source: Path,
    output: Path,
    convert_audio: ConvertAudioFn,
    work_dir: Path,
    sample_rate: int = 40_000,
) -> MediaResult:
    """Convert ``source`` to ``output`` using ``convert_audio`` for the voice work.

    * audio input → extract-normalize → convert → write output audio.
    * video input → extract audio → convert → remux into original video
      (video stream bit-identical, subtitles/metadata preserved).
    """
    ensure_ffmpeg()
    source = Path(source)
    output = Path(output)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    info = probe(source)
    stem = source.stem

    extracted = work_dir / f"{stem}.src.wav"
    extract_audio(source, extracted, sample_rate=sample_rate, channels=1)

    converted = work_dir / f"{stem}.conv.wav"
    convert_audio(extracted, converted)

    if not converted.exists():
        raise MediaError("convert_audio did not produce an output file.")

    if info.is_video:
        remux_audio(source, converted, output)
        out_info = probe(output)
        _check_duration(info.duration, out_info.duration)
        return MediaResult(kind="video", output=output, duration=out_info.duration)

    # Audio-only: transcode converted WAV into the requested output container.
    from voicemorph_media.ffmpeg import _run, _which  # local import: internal helpers

    _run([_which("ffmpeg"), "-y", "-i", str(converted), str(output)])
    out_info = probe(output)
    _check_duration(info.duration, out_info.duration)
    return MediaResult(kind="audio", output=output, duration=out_info.duration)


def _check_duration(src: float, out: float) -> None:
    if src > 0 and abs(src - out) > DURATION_TOLERANCE_SECONDS:
        raise MediaError(
            f"Output duration {out:.3f}s drifted from source {src:.3f}s beyond tolerance "
            f"({DURATION_TOLERANCE_SECONDS}s). Timing preservation violated."
        )
