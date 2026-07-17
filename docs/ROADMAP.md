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

## M3 — Backend batch API + job queue
- [ ] FastAPI service, API-key auth
- [ ] Celery + Redis job queue, MinIO storage
- [ ] `POST /voices`, `GET /voices/{id}/status`, `POST /convert/batch`, `GET /convert/batch/{job_id}`
- [ ] Docker images (GPU worker + light API) + compose

## M4 — Desktop app (batch)
- [ ] Tauri + React/TS shell; server-config screen
- [ ] Voice-profile library UI; drag-and-drop convert; preview/download
- [ ] `.exe` installer build (+ macOS/Linux targets)

## M5 — Real-time streaming (backend)
- [ ] `WS /convert/stream/{voice_id}`, chunked inference, warm model pool
- [ ] Latency budget ≤ ~300 ms on consumer GPU; RTF metrics

## M6 — Desktop live mode
- [ ] Mic capture → stream → converted output; virtual audio device routing

## M7 — Mobile app
- [ ] React Native: record/import target, batch convert, save result
- [ ] Live mode over WebSocket
- [ ] Signed `.apk` / `.aab`

## M8 — Packaging, signing, distribution
- [ ] Code-signing (Windows), Play-signing (Android)
- [ ] Release CI/CD, versioned artifacts
