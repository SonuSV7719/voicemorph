# Roadmap

Ordered by the build priorities in the master prompt. Each milestone is a vertical slice we can verify.

## M1 — Engine: batch conversion on CLI  ⬅ current
- [x] Monorepo scaffold, license, ethics notice
- [x] Engine package skeleton + pluggable backend interface
- [x] Voice-profile registry with mandatory consent record
- [x] Media I/O layer (probe / extract / remux) — **verifiable without GPU**
- [ ] RVC backend: preprocessing pipeline (resample/trim/slice)
- [ ] RVC backend: feature + RMVPE pitch extraction
- [ ] RVC backend: training → `.pth` + `.index`
- [ ] RVC backend: batch inference (duration-preserving)
- [ ] `voicemorph` CLI: `profile create`, `train`, `convert`
- [ ] End-to-end CLI demo on a real target voice (proves quality)

## M2 — Media round-trip verified
- [ ] Video in → audio extracted → converted → remuxed; video stream bit-identical, subs/metadata preserved, duration within tolerance
- [ ] Golden-file tests for common containers (mp4/mov/mkv)

## M3 — Backend batch API + job queue  ⬅ in progress
- [x] FastAPI service, API-key auth
- [x] Celery + Redis job queue (eager fallback for dev), S3/MinIO + local storage
- [x] `POST /voices`, `GET /voices/{id}/status`, `POST /convert/batch`, `GET /convert/batch/{job_id}` (+ `/download`)
- [x] Docker images (GPU worker + light API) + compose
- [x] `passthrough` engine backend so the full pipeline is CPU-testable end-to-end
- [x] End-to-end API test: create → train → convert → download (CPU)
- [ ] Streaming WS hardened + load-tested (overlaps with M5)

## M4 — Desktop app (batch)  ⬅ in progress
- [x] Tauri v2 + React/TS shell; server-config screen (test connection)
- [x] Typed backend API client (mirrors backend schemas)
- [x] Voice-profile library UI (consent-gated create + status polling)
- [x] Drag-and-drop batch convert; progress; download (audio/video)
- [ ] Icons + `.exe`/`.msi` installer build verified (needs Rust/WebView2 + icon assets)
- [ ] macOS/Linux target builds

## M5 — Real-time streaming (backend)
- [x] `WS /convert/stream/{voice_id}` — chunked inference, resident model, threaded convert bridge
- [x] 1:1 chunk contract with blocking receive (off the event loop); crossfade seam smoothing
- [x] End-to-end WS test (identity via passthrough) + bad-key rejection
- [x] Example streaming client (`examples/stream_client.py`) documenting the wire format
- [ ] Latency budget ≤ ~300 ms on consumer GPU; RTF metrics (needs GPU + real RVC)
- [ ] Warm model pool / LRU eviction under load (M5 hardening on GPU)

## M6 — Desktop live mode
- [x] Mic capture (AudioWorklet) → WebSocket stream → converted playback (AudioWorklet)
- [x] Live view wired into the desktop app (voice selector, start/stop, status)
- [ ] Virtual audio device routing (output to a VB-Cable-style device for calls/streaming)

## M7 — Mobile app  ⬅ in progress
- [x] React Native (Expo) + TS shell; server-config screen (test connection)
- [x] Typed backend client (RN FormData uploads); AsyncStorage config
- [x] Voice library (consent-gated create via document picker, status polling)
- [x] Batch convert (pick audio/video, convert, save result to device)
- [ ] Live mode over WebSocket
- [ ] Signed `.apk` / `.aab` via EAS (needs Expo account / Android SDK)

## M8 — Packaging, signing, distribution
- [x] Release CI: desktop installers via tauri-action (win/mac/linux) on `vX.Y.Z` tag
- [x] Release CI: Android APK/AAB via Expo EAS on tag
- [x] Release guide (`docs/RELEASE.md`): signing secrets, icons, versioning
- [ ] Provision signing certs/keystores (Windows Authenticode, Apple notarization, Play keystore)
