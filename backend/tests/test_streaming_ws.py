"""Real-time streaming over the WebSocket, end-to-end on CPU.

With the passthrough backend the converter is identity, so every float32 PCM
frame sent must come back unchanged and length-preserved — proving the streaming
path (auth, resident model, threaded convert bridge, framing) works.
"""

from __future__ import annotations

import json
import struct

import numpy as np


def _train_ready_voice(client, auth, wav_factory) -> str:
    sample = wav_factory("sample.wav", seconds=2.0)
    r = client.post(
        "/voices",
        headers=auth,
        data={
            "name": "Alex",
            "consent": json.dumps({"subject": "Alex", "confirmed": True}),
            "epochs": 1,
        },
        files={"files": ("sample.wav", sample.read_bytes(), "audio/wav")},
    )
    assert r.status_code == 200, r.text
    voice_id = r.json()["voice_id"]
    assert client.get(f"/voices/{voice_id}/status", headers=auth).json()["ready"] is True
    return voice_id


def _pcm(frame: np.ndarray) -> bytes:
    return frame.astype("<f4").tobytes()


def test_ws_streaming_identity(client, auth, wav_factory):
    voice_id = _train_ready_voice(client, auth, wav_factory)

    frames = [
        np.linspace(-0.5, 0.5, 4800, dtype=np.float32),
        np.full(4800, 0.25, dtype=np.float32),
        np.sin(np.linspace(0, 6.28, 4800)).astype(np.float32),
    ]

    with client.websocket_connect(f"/convert/stream/{voice_id}?api_key=test-key") as ws:
        for frame in frames:
            ws.send_bytes(_pcm(frame))
            data = ws.receive_bytes()
            got = np.frombuffer(data, dtype="<f4")
            assert got.shape == frame.shape           # length preserved
            assert np.allclose(got, frame, atol=1e-6)  # identity (passthrough)


def test_ws_rejects_bad_api_key(client, auth, wav_factory):
    voice_id = _train_ready_voice(client, auth, wav_factory)
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(f"/convert/stream/{voice_id}?api_key=wrong") as ws,
    ):
        ws.send_bytes(struct.pack("<f", 0.0))
        ws.receive_bytes()
