# VoiceMorph

> Enterprise-grade, cross-platform **voice conversion** (speech-to-speech). Convert *whose* voice a recording sounds like — while preserving *what* was said, the timing, pacing, and emotional delivery of the original speaker.

VoiceMorph is **voice conversion (VC)**, not text-to-speech. No script is typed. Given a **target voice sample** and **any source audio or video**, it produces output where the words, prosody (pitch contour, rhythm, pauses, stress) and emotion are exactly as originally spoken — only the vocal timbre/identity is converted.

- **Video in → video out**: same visuals, same timing, video stream bit-identical; only the audio track's voice is converted.
- **Audio in → audio out**: same container and duration.
- **Two modes**: offline **batch** conversion and low-latency **real-time** streaming (≤ ~300 ms on consumer GPU).
- **Native clients**: Windows `.exe` (Tauri desktop, cross-buildable to macOS/Linux) and Android `.apk` (React Native), both talking to a self- or cloud-hosted GPU backend.

---

## ⚖️ Ethical use — read before you build

VoiceMorph converts **existing spoken audio only**. It does **not** fabricate dialogue.

**You must have the right to use every target voice** — your own, or one for which you have explicit, documented consent. VoiceMorph must not be used to impersonate people without consent, to bypass voice-authentication systems, or to produce deceptive content. Each voice profile requires an explicit consent confirmation before training. See [`NOTICE`](./NOTICE) and [`docs/ETHICS.md`](./docs/ETHICS.md).

---

## Architecture

VoiceMorph is a monorepo. The heavy ML work is GPU-bound and lives in the **backend inference server**; native apps are **clients** (the desktop app can optionally bundle a local server when a GPU is present).

```
voicemorph/
├── engine/     Python — RVC training + batch/streaming inference (RMVPE pitch)
├── backend/    FastAPI + Celery/Redis + MinIO(S3) — REST + WebSocket, API-key auth
├── media/      ffmpeg extract/remux — video untouched, audio swapped, sync-safe
├── apps/
│   ├── desktop/   Tauri + React/TS  → .exe / .dmg / .AppImage
│   └── mobile/    React Native      → .apk / .aab
├── docker/     GPU inference image + light API image + docker-compose
├── infra/      k8s/helm, CI/CD, observability (scale-out inference workers)
└── docs/       architecture, engine, API, ethics
```

See [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for the full design and the honest GPU constraint.

---

## Build priorities

1. **Engine**: training + batch inference working end-to-end on CLI (prove quality first). ← *current focus*
2. **Media I/O**: video extract/convert/remux round-trip verified.
3. Backend batch API + job queue.
4. Desktop app: batch-mode UI.
5. Backend real-time WebSocket streaming.
6. Desktop app: live mode.
7. Mobile app: batch then live.
8. Packaging/signing/distribution for EXE and APK.

---

## Quick start (development)

Requirements: Python 3.10–3.11 (recommended for the RVC/PyTorch stack), Node 20+, Docker, `ffmpeg` on PATH, and an NVIDIA GPU + CUDA for training/inference.

```bash
# Engine (editable install)
cd engine
python -m venv .venv && . .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Verify the media round-trip (no GPU needed)
voicemorph-media probe path/to/input.mp4
```

> **Python version note:** this machine has Python 3.13, but the RVC/PyTorch ecosystem is currently most stable on **3.10/3.11**. Use `pyenv`/`conda` to pin an engine interpreter. The `media` and `backend` layers work fine on 3.13.

---

## Status

🚧 Early development. Engine and media layers first. See [issues](https://github.com/SonuSV7719/voicemorph/issues) and [`docs/ROADMAP.md`](./docs/ROADMAP.md).

## License

[Apache-2.0](./LICENSE) with the additional ethical-use notice in [`NOTICE`](./NOTICE).
