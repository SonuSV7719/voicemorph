# API reference

Base URL: `http://<host>:8000` (dev). Interactive docs are served at `/docs`
(Swagger UI) and `/redoc` when the backend is running.

## Authentication

All endpoints except `/health` require an API key, sent as either header:

```
X-API-Key: <key>
# or
Authorization: Bearer <key>
```

The key is configured with `VOICEMORPH_API_KEY`. WebSocket clients pass it as a
query parameter: `?api_key=<key>`.

---

## REST

### `GET /health`

Liveness + active configuration. No auth.

```json
{ "status": "ok", "engine_backend": "passthrough", "job_mode": "eager" }
```

### `POST /voices`

Create a **consent-gated** voice profile from uploaded samples and start
training. `multipart/form-data`.

| Field | Type | Notes |
|---|---|---|
| `name` | string | Display name |
| `consent` | string (JSON) | `{"subject","granted_by?","method?","reference?","confirmed"}` — `confirmed` **must** be `true` |
| `epochs` | int | default 200 |
| `files` | file[] | target-voice samples |

```bash
curl -sS -X POST http://127.0.0.1:8000/voices \
  -H "X-API-Key: $KEY" \
  -F 'name=My Voice' \
  -F 'consent={"subject":"Me","confirmed":true,"method":"self"}' \
  -F 'files=@sample1.wav' -F 'files=@sample2.wav'
```

```json
{ "voice_id": "9f2c…", "name": "My Voice", "status": "created" }
```

`422` if consent is not confirmed. Training then runs in the background — poll status.

### `GET /voices/{voice_id}/status`

```json
{ "voice_id": "9f2c…", "name": "My Voice", "status": "ready",
  "ready": true, "error": null, "dataset_seconds": 742.5 }
```

`status` ∈ `created | preprocessing | training | ready | failed`. `404` if unknown.

### `POST /convert/batch`

Queue a conversion. `multipart/form-data`.

| Field | Type | Default |
|---|---|---|
| `voice_id` | string | — |
| `file` | file | — (audio or video) |
| `transpose` | int | `0` (semitones; 0 keeps source register) |
| `index_rate` | float | `0.75` |
| `protect` | float | `0.33` |

```bash
curl -sS -X POST http://127.0.0.1:8000/convert/batch \
  -H "X-API-Key: $KEY" \
  -F "voice_id=$VOICE" -F 'file=@input.mp4'
```

Returns a job:

```json
{ "job_id": "1a2b…", "kind": "convert", "state": "queued", "progress": 0.0,
  "voice_id": "9f2c…", "result_key": null, "output_kind": null, "error": null }
```

### `GET /convert/batch/{job_id}`

Poll job state. `state` ∈ `queued | running | succeeded | failed`. On success,
`output_kind` is `audio` or `video` and `result_key` is set.

### `GET /convert/batch/{job_id}/download`

Stream the converted result. `409` if the job has no result yet; `404` if unknown.

```bash
curl -sS -H "X-API-Key: $KEY" -OJ \
  http://127.0.0.1:8000/convert/batch/$JOB/download
```

---

## WebSocket — real-time streaming

```
WS /convert/stream/{voice_id}?api_key=<key>
```

- **Wire format:** binary frames of **little-endian float32 mono PCM** at the
  backend sample rate (default 40 kHz), in **and** out.
- The model is loaded once and stays resident for the session.
- The backend returns roughly one converted frame per input frame (1:1),
  applying an equal-power crossfade at seams.
- Close codes: `4401` bad/missing key, `4404` unknown or untrained voice.

A complete client is in [`examples/stream_client.py`](../examples/stream_client.py);
the desktop **Live** mode uses the same protocol from the browser via AudioWorklets.

```python
import asyncio, numpy as np, soundfile as sf, websockets

async def main():
    audio, sr = sf.read("in.wav", dtype="float32")
    async with websockets.connect(
        f"ws://127.0.0.1:8000/convert/stream/{VOICE}?api_key={KEY}", max_size=None
    ) as ws:
        out = []
        for i in range(0, len(audio), int(0.3 * sr)):
            await ws.send(audio[i:i+int(0.3*sr)].astype("<f4").tobytes())
            out.append(np.frombuffer(await ws.recv(), dtype="<f4"))
    sf.write("out.wav", np.concatenate(out), sr)

asyncio.run(main())
```

---

## Errors

Standard JSON error bodies: `{ "detail": "<message>" }`. Common codes: `401`
(auth), `404` (not found), `409` (not ready), `422` (validation / consent).
