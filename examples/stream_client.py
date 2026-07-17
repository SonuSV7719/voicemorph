"""Example real-time streaming client for VoiceMorph.

Streams a WAV file to the backend's WebSocket endpoint in fixed chunks and
writes the converted audio back out. Demonstrates the wire format the desktop
live mode (M6) and mobile live mode (M7) use.

Wire format: little-endian float32 mono PCM frames, in and out.

Requires: pip install websockets soundfile numpy

Usage:
    python examples/stream_client.py \
        --url ws://127.0.0.1:8000 --api-key dev \
        --voice <voice_id> --in input.wav --out converted.wav
"""

from __future__ import annotations

import argparse
import asyncio

import numpy as np
import soundfile as sf

try:
    import websockets
except ImportError as exc:  # pragma: no cover - example script
    raise SystemExit("Install websockets: pip install websockets") from exc


async def stream(url: str, api_key: str, voice_id: str, in_path: str, out_path: str,
                 chunk_seconds: float = 0.3) -> None:
    audio, sr = sf.read(in_path, dtype="float32", always_2d=False)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    chunk = int(chunk_seconds * sr)

    endpoint = f"{url.rstrip('/')}/convert/stream/{voice_id}?api_key={api_key}"
    out_frames: list[np.ndarray] = []

    async with websockets.connect(endpoint, max_size=None) as ws:
        for i in range(0, len(audio), chunk):
            frame = audio[i : i + chunk].astype("<f4")
            await ws.send(frame.tobytes())
            data = await ws.recv()
            out_frames.append(np.frombuffer(data, dtype="<f4"))

    converted = np.concatenate(out_frames) if out_frames else np.zeros(0, dtype=np.float32)
    sf.write(out_path, converted, sr)
    print(f"Wrote {out_path} ({len(converted) / sr:.2f}s)")


def main() -> None:
    ap = argparse.ArgumentParser(description="VoiceMorph streaming client example")
    ap.add_argument("--url", default="ws://127.0.0.1:8000")
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--voice", required=True)
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", dest="out_path", default="converted.wav")
    args = ap.parse_args()
    asyncio.run(stream(args.url, args.api_key, args.voice, args.in_path, args.out_path))


if __name__ == "__main__":
    main()
