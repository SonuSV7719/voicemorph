# VoiceMorph — Architecture

## 1. What it is (and is not)

VoiceMorph performs **voice conversion (VC)**: it takes real spoken audio and re-renders it in a **target voice's timbre** while preserving the *content* (every word) and *delivery* (F0/pitch contour, rhythm, pauses, stress, emotion) of the **original speaker**.

It is **not** text-to-speech. There is no transcription-and-resynthesis step. TTS would regenerate prosody from scratch and lose the original delivery; VC keeps the source's pitch contour and timing and only swaps vocal-tract/timbre characteristics.

## 2. The honest GPU constraint

VC inference is GPU-bound and heavy. Design consequences (non-negotiable):

- The **backend inference server** does all training + inference on a GPU machine/cloud instance.
- Native apps (**EXE/APK**) are **clients**: capture/upload audio or video over REST (batch) and WebSocket (real-time), receive results.
- The **desktop EXE** may *optionally* bundle and run the inference server locally when a GPU is present → "fully local" experience.
- The **Android APK** is always a thin client (mobile GPUs are insufficient). We do **not** ship an on-device mobile ML model — it would silently degrade quality.

## 3. Component map

```
┌──────────────┐        REST (batch)         ┌───────────────────────────────┐
│ Desktop (EXE)│ ─────────────────────────▶ │ Backend API (FastAPI)         │
│ Tauri+React  │ ◀───────────────────────── │  /voices  /convert/batch      │
└──────────────┘        WS (real-time)       │  WS /convert/stream           │
┌──────────────┐ ─────────────────────────▶ └───────────────┬───────────────┘
│ Mobile (APK) │ ◀─────────────────────────                 │ enqueue
│ React Native │                                            ▼
└──────────────┘                              ┌───────────────────────────────┐
                                              │ Celery workers (GPU)          │
                                              │  training jobs / batch convert│
                                              │  → engine (RVC + RMVPE)       │
                                              └───────────────┬───────────────┘
                                     models/artifacts         │
                                              ┌───────────────▼───────────────┐
                                              │ Redis (broker) · MinIO/S3      │
                                              └───────────────────────────────┘
```

## 4. Engine (`engine/`)

Pluggable VC backend behind a stable interface (`backends/base.py::VoiceConversionBackend`) so the RVC implementation can be swapped/upgraded without touching callers.

- **Preprocessing** (`preprocessing.py`): resample → mono → trim silence → slice into training clips.
- **Feature/pitch extraction** (`features.py`): **RMVPE** for F0 (best-practice for RVC pipelines), content features via the RVC feature extractor (HuBERT/ContentVec).
- **Training** (`training.py`): folder of target-voice clips → `.pth` model + `.index` retrieval file, stored per `voice_id`.
- **Batch inference** (`inference.py`): source audio + `voice_id` → converted audio, **duration preserved exactly**.
- **Streaming inference** (`streaming.py`): chunked (0.2–0.5 s buffers), model resident in GPU memory, tunable crossfade; target ≤ ~300 ms end-to-end.
- **Profiles** (`profiles.py`): per-voice metadata, training status, and a required **consent record**.

### Data flow (batch)

```
video? ──ffmpeg──▶ extract audio ─┐
audio? ───────────────────────────┤─▶ engine.convert(voice_id) ─▶ converted audio
                                   │                                     │
video? ◀──ffmpeg remux (video bit-identical, subs/metadata kept)◀───────┘
audio? ◀── converted audio (same container/duration) ◀───────────────────
```

## 5. Media I/O (`media/`)

Thin, well-tested `ffmpeg`/`ffprobe` wrapper shared by the backend:

- **probe**: detect audio-only vs video; report streams, duration, codecs.
- **extract**: pull the audio track to a canonical WAV for the engine.
- **remux**: mux converted audio back into the *original* container, copying the video stream (`-c:v copy`, bit-identical) and preserving subtitle/metadata streams.
- **duration/sync guard**: verify output duration matches input within tolerance.

## 6. Backend (`backend/`) — later phase

FastAPI + Celery + Redis + MinIO. Endpoints: `POST /voices`, `GET /voices/{id}/status`, `POST /convert/batch`, `GET /convert/batch/{job_id}`, `WS /convert/stream/{voice_id}`. API-key auth. Containerized: heavy GPU worker image + light API image.

## 7. Scalability & optimization (enterprise targets)

- **Horizontal scale-out** of GPU workers behind Celery; queue-based backpressure.
- **Model residency & warm pools**: keep hot voice models in GPU memory; LRU eviction; per-voice worker affinity to avoid reloads.
- **Streaming path** kept separate from batch (latency-sensitive) — dedicated worker class, no queueing.
- **Object storage** for models/artifacts; CDN for result download.
- **Observability**: structured logs, Prometheus metrics (latency, RTF — real-time factor, GPU util), tracing.
- **Zero-copy media**: stream extract→convert→remux without full-file buffering where possible.

## 8. Security & ethics

API-key/token auth for personal servers. Every voice profile carries a consent record; training refuses without an explicit consent flag. See [`ETHICS.md`](./ETHICS.md).
