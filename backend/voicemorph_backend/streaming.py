"""Real-time streaming conversion session (WebSocket backing).

Bridges the engine's blocking ``convert_stream(iterable) -> iterator`` to an
incremental push/pull model suitable for a WebSocket: a worker thread runs the
converter over a queue-backed generator, so the model stays resident for the
whole session and each pushed chunk is converted with crossfade state carried
across chunks.

Wire format: little-endian float32 mono PCM frames at the negotiated sample
rate, in and out.
"""

from __future__ import annotations

import queue
import threading

import numpy as np
from voicemorph_engine.backends.base import (
    ConversionParams,
    StreamConfig,
    VoiceConversionBackend,
)

_SENTINEL = object()


class StreamSession:
    def __init__(
        self,
        backend: VoiceConversionBackend,
        voice_id: str,
        params: ConversionParams,
        stream_config: StreamConfig,
    ):
        self._in: queue.Queue = queue.Queue(maxsize=64)
        self._out: queue.Queue = queue.Queue(maxsize=64)
        self._error: Exception | None = None

        def _gen():
            while True:
                item = self._in.get()
                if item is _SENTINEL:
                    return
                yield item

        def _run():
            try:
                for out in backend.convert_stream(voice_id, _gen(), params, stream_config):
                    self._out.put(out)
            except Exception as exc:  # surface to the reader
                self._error = exc
            finally:
                self._out.put(_SENTINEL)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def push(self, chunk: np.ndarray) -> None:
        self._in.put(np.asarray(chunk, dtype=np.float32))

    def drain(self) -> list[np.ndarray]:
        """Return any converted chunks available right now (non-blocking)."""
        out: list[np.ndarray] = []
        while True:
            try:
                item = self._out.get_nowait()
            except queue.Empty:
                break
            if item is _SENTINEL:
                break
            out.append(item)
        if self._error:
            raise self._error
        return out

    def close(self) -> list[np.ndarray]:
        """Signal end-of-stream and collect remaining converted chunks."""
        self._in.put(_SENTINEL)
        out: list[np.ndarray] = []
        while True:
            item = self._out.get()
            if item is _SENTINEL:
                break
            out.append(item)
        if self._error:
            raise self._error
        return out


def bytes_to_float32(data: bytes) -> np.ndarray:
    return np.frombuffer(data, dtype="<f4").copy()


def float32_to_bytes(arr: np.ndarray) -> bytes:
    return np.asarray(arr, dtype="<f4").tobytes()
