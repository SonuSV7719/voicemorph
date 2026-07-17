"""Preprocessing: resample, silence trimming/splitting, slicing."""

from __future__ import annotations

import numpy as np
import soundfile as sf

from voicemorph_engine.preprocessing import PreprocessConfig, preprocess_dataset


def _tone(freq: float, seconds: float, sr: int) -> np.ndarray:
    t = np.linspace(0.0, seconds, int(seconds * sr), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_splits_on_silence_and_resamples(tmp_path):
    src_sr = 16_000
    speech_a = _tone(220.0, 2.0, src_sr)
    silence = np.zeros(int(0.6 * src_sr), dtype=np.float32)
    speech_b = _tone(330.0, 2.0, src_sr)
    signal = np.concatenate([speech_a, silence, speech_b])

    in_dir = tmp_path / "raw"
    in_dir.mkdir()
    sf.write(str(in_dir / "take1.wav"), signal, src_sr)

    out_dir = tmp_path / "dataset"
    report = preprocess_dataset(in_dir, out_dir, PreprocessConfig(target_sr=40_000))

    assert report.input_files == 1
    # Two voiced regions separated by silence → at least two clips.
    assert report.clips_written >= 2

    clips = sorted(out_dir.glob("clip_*.wav"))
    assert clips
    data, sr = sf.read(str(clips[0]), dtype="float32")
    assert sr == 40_000                 # resampled to canonical rate
    assert data.ndim == 1               # mono
    assert float(np.max(np.abs(data))) <= 0.96  # peak-normalized
