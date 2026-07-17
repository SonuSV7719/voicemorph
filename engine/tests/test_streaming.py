"""Streaming converter DSP: length preservation and seam smoothing.

Uses a fake identity session (no ML deps) so the pure-NumPy DSP is testable.
"""

from __future__ import annotations

import numpy as np

from voicemorph_engine.backends._rvc_driver import StreamingConverter
from voicemorph_engine.backends.base import ConversionParams, StreamConfig


class _IdentitySession:
    """Stands in for a resident RVC session; returns audio unchanged."""

    def infer_array(self, chunk: np.ndarray, sr: int) -> np.ndarray:
        return np.asarray(chunk, dtype=np.float32)


def test_streaming_preserves_total_length():
    sr = 16_000
    cfg = StreamConfig(chunk_seconds=0.2, crossfade_seconds=0.02, sample_rate=sr)
    conv = StreamingConverter(_IdentitySession(), ConversionParams(), cfg)

    chunk_len = int(cfg.chunk_seconds * sr)
    chunks = [np.full(chunk_len, i + 1, dtype=np.float32) for i in range(5)]

    out = []
    for c in chunks:
        out.append(conv.process(c))
    tail = conv.flush()
    if tail is not None:
        out.append(tail)

    total_in = sum(len(c) for c in chunks)
    total_out = sum(len(o) for o in out)
    assert total_out == total_in  # timing preserved exactly


def test_seam_is_blended_not_hard_edge():
    sr = 16_000
    xfade_s = 0.02
    cfg = StreamConfig(chunk_seconds=0.2, crossfade_seconds=xfade_s, sample_rate=sr)
    conv = StreamingConverter(_IdentitySession(), ConversionParams(), cfg)

    a = np.zeros(int(cfg.chunk_seconds * sr), dtype=np.float32)  # silence
    b = np.ones(int(cfg.chunk_seconds * sr), dtype=np.float32)   # full level
    conv.process(a)
    out_b = conv.process(b)

    xfade = int(xfade_s * sr)
    # The seam region ramps up rather than jumping 0 -> 1 instantly.
    assert out_b[0] < 0.5
    assert out_b[xfade] >= 0.99
    assert np.all(np.diff(out_b[:xfade]) >= -1e-6)  # monotonic ramp in
