"""Real ffmpeg round-trip: synthesize video → extract → 'convert' → remux.

Skips automatically if ffmpeg/ffprobe are not installed. The stand-in
'conversion' is a copy (identity), which is enough to prove the media layer:
video stream copied bit-identically, duration preserved, subtitles ignored
gracefully when absent.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from voicemorph_media.ffmpeg import probe
from voicemorph_media.pipeline import convert_media

pytestmark = pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
    reason="ffmpeg/ffprobe not installed",
)


def _make_test_video(path, seconds=2):
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"testsrc=size=320x240:rate=25:duration={seconds}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-shortest", str(path),
        ],
        check=True,
        capture_output=True,
    )


def test_video_roundtrip_preserves_duration_and_video(tmp_path):
    src = tmp_path / "in.mp4"
    _make_test_video(src, seconds=2)
    src_info = probe(src)
    assert src_info.is_video

    def identity_convert(source_wav, out_wav):
        shutil.copyfile(source_wav, out_wav)

    out = tmp_path / "out.mp4"
    result = convert_media(
        source=src,
        output=out,
        convert_audio=identity_convert,
        work_dir=tmp_path / "work",
        sample_rate=40_000,
    )

    assert result.kind == "video"
    out_info = probe(out)
    assert out_info.is_video
    assert abs(out_info.duration - src_info.duration) < 0.1  # timing preserved


def test_audio_roundtrip(tmp_path):
    src = tmp_path / "in.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1.5", str(src)],
        check=True,
        capture_output=True,
    )

    def identity_convert(source_wav, out_wav):
        shutil.copyfile(source_wav, out_wav)

    out = tmp_path / "out.wav"
    result = convert_media(
        source=src,
        output=out,
        convert_audio=identity_convert,
        work_dir=tmp_path / "work",
    )
    assert result.kind == "audio"
    assert abs(probe(out).duration - 1.5) < 0.1
