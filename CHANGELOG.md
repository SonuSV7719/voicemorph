# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Engine (M1):** backend-agnostic `VoiceConversionBackend` interface; RVC
  backend with the third-party call surface isolated in `_rvc_driver`;
  consent-gated voice-profile registry; preprocessing (resample/trim/slice);
  length-preserving streaming converter; `voicemorph` CLI. A `passthrough`
  (identity) backend makes the whole pipeline testable on CPU.
- **Media (M2):** `ffmpeg`/`ffprobe` wrapper — probe/extract/remux with the video
  stream copied bit-identical and subtitles/metadata preserved; audio-vs-video
  routing; `voicemorph-media` CLI.
- **Backend (M3):** FastAPI REST + WebSocket API; API-key auth; Celery/Redis job
  queue (eager fallback for dev); local + S3/MinIO storage; Docker images (light
  API + GPU worker) and docker-compose.
- **Desktop (M4):** Tauri v2 + React/TS batch-mode app — server config, voice
  library, drag-and-drop convert with progress and download.
- **Streaming (M5):** hardened real-time WebSocket path (1:1 chunk contract,
  resident model), end-to-end tests, and an example streaming client.
- **Desktop live mode (M6):** AudioWorklet mic capture → WebSocket → AudioWorklet
  playback; "Live" tab.
- **Mobile (M7):** React Native (Expo) + TS Android client — batch mode with
  consent-gated profiles and file picking.
- **Release (M8):** desktop (`tauri-action`) and Android (Expo EAS) release
  workflows on version tags; `docs/RELEASE.md`.
- **Docs & community health:** professional README; ARCHITECTURE, API,
  CONFIGURATION, DEPLOYMENT, DEVELOPMENT, ENGINE, ETHICS, FAQ, RELEASE, ROADMAP;
  CODE_OF_CONDUCT, CONTRIBUTING, SECURITY, SUPPORT; issue/PR templates,
  CODEOWNERS, Dependabot.

### Notes
- Real RVC training/inference requires Python 3.10/3.11 + an NVIDIA GPU + model
  weights; set `VOICEMORPH_ENGINE_BACKEND=rvc`. The default `passthrough` backend
  performs no conversion and is for development/CI only.

[Unreleased]: https://github.com/SonuSV7719/voicemorph/commits/main
