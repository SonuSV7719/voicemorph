"""Dataset preprocessing for per-voice training.

Turns a folder of raw target-voice recordings into clean, canonical-rate mono
clips ready for RVC feature extraction:

    resample → mono → normalize → trim leading/trailing silence → slice on pauses

I/O uses ``soundfile`` (always available). Resampling uses ``librosa`` when the
``[ml]`` extra is installed, and falls back to a dependency-free linear
resampler otherwise so preprocessing runs on any interpreter.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from voicemorph_engine.config import CANONICAL_SAMPLE_RATE

AUDIO_EXTENSIONS = {".wav", ".flac", ".mp3", ".ogg", ".m4a", ".aac", ".opus"}


@dataclass
class PreprocessConfig:
    target_sr: int = CANONICAL_SAMPLE_RATE
    # Slice long recordings into clips of at most this many seconds.
    max_clip_seconds: float = 8.0
    min_clip_seconds: float = 1.0
    # Silence detection for trimming/splitting.
    silence_db: float = -40.0          # below this RMS (dBFS) is "silence"
    min_silence_seconds: float = 0.3   # gap length that triggers a split
    peak_normalize: float = 0.95       # normalize peak to this amplitude


@dataclass
class PreprocessReport:
    input_files: int
    clips_written: int
    total_seconds: float
    output_dir: Path


def _to_mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 2:
        return audio.mean(axis=1)
    return audio


def _resample(audio: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    if src_sr == dst_sr:
        return audio.astype(np.float32)
    try:
        import librosa

        return librosa.resample(audio.astype(np.float32), orig_sr=src_sr, target_sr=dst_sr)
    except Exception:
        # Dependency-free linear resampler (adequate for preprocessing; librosa
        # gives higher quality and is used when the [ml] extra is present).
        duration = audio.shape[0] / src_sr
        n_out = int(round(duration * dst_sr))
        if n_out <= 1:
            return audio.astype(np.float32)
        x_old = np.linspace(0.0, 1.0, num=audio.shape[0], endpoint=False)
        x_new = np.linspace(0.0, 1.0, num=n_out, endpoint=False)
        return np.interp(x_new, x_old, audio).astype(np.float32)


def _rms_db(frame: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(np.square(frame)) + 1e-12))
    return 20.0 * np.log10(rms + 1e-12)


def _non_silent_intervals(
    audio: np.ndarray, sr: int, silence_db: float, min_silence_seconds: float
) -> list[tuple[int, int]]:
    """Return [start, end) sample intervals of non-silent audio."""
    frame = max(1, int(0.02 * sr))  # 20 ms frames
    hop = frame
    voiced: list[bool] = []
    for i in range(0, len(audio) - frame + 1, hop):
        voiced.append(_rms_db(audio[i : i + frame]) > silence_db)
    if not voiced:
        return [(0, len(audio))]

    min_sil_frames = max(1, int(min_silence_seconds / (hop / sr)))
    intervals: list[tuple[int, int]] = []
    run_start: int | None = None
    silence_run = 0
    for idx, is_voiced in enumerate(voiced):
        if is_voiced:
            if run_start is None:
                run_start = idx
            silence_run = 0
        else:
            if run_start is not None:
                silence_run += 1
                if silence_run >= min_sil_frames:
                    intervals.append((run_start * hop, (idx - silence_run + 1) * hop))
                    run_start = None
                    silence_run = 0
    if run_start is not None:
        intervals.append((run_start * hop, len(audio)))
    return intervals or [(0, len(audio))]


def preprocess_dataset(
    input_dir: Path, output_dir: Path, config: PreprocessConfig | None = None
) -> PreprocessReport:
    """Preprocess every audio file in ``input_dir`` into clips under ``output_dir``."""
    config = config or PreprocessConfig()
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = [
        p for p in sorted(input_dir.rglob("*")) if p.suffix.lower() in AUDIO_EXTENSIONS
    ]
    clip_idx = 0
    total_seconds = 0.0
    max_len = int(config.max_clip_seconds * config.target_sr)
    min_len = int(config.min_clip_seconds * config.target_sr)

    for src in sources:
        audio, sr = sf.read(str(src), dtype="float32", always_2d=False)
        audio = _to_mono(np.asarray(audio, dtype=np.float32))
        audio = _resample(audio, sr, config.target_sr)

        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        if peak > 0:
            audio = audio * (config.peak_normalize / peak)

        for start, end in _non_silent_intervals(
            audio, config.target_sr, config.silence_db, config.min_silence_seconds
        ):
            segment = audio[start:end]
            # Split segments longer than max_len into fixed windows.
            for off in range(0, len(segment), max_len):
                clip = segment[off : off + max_len]
                if len(clip) < min_len:
                    continue
                out = output_dir / f"clip_{clip_idx:05d}.wav"
                sf.write(str(out), clip, config.target_sr)
                clip_idx += 1
                total_seconds += len(clip) / config.target_sr

    return PreprocessReport(
        input_files=len(sources),
        clips_written=clip_idx,
        total_seconds=total_seconds,
        output_dir=output_dir,
    )
