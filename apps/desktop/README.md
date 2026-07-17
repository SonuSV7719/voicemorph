# voicemorph-desktop (M4)

Tauri v2 + React/TypeScript desktop client. Talks to a VoiceMorph backend over
HTTP (batch) — a local bundled server, a LAN machine, or a cloud endpoint.

## Features (batch mode)

- **Server** — point the app at a backend URL + API key; test the connection.
- **Voices** — create a consent-gated profile from uploaded samples; watch
  training status; manage a local library.
- **Convert** — drag-and-drop an audio/video file, pick a target voice, convert,
  track progress, and download the result (audio→audio, video→video).

- **Live** — real-time mic conversion: AudioWorklet capture → backend WebSocket
  → AudioWorklet playback. Virtual-audio-device routing (for calls/streaming) is
  a follow-up.

## Develop

```bash
cd apps/desktop
npm install
npm run dev            # web frontend only (http://localhost:1420)
npm run tauri:dev      # full desktop app (requires Rust + WebView2)
```

## Build installers

```bash
# One-time: generate icons from a 1024x1024 PNG (Tauri needs them to bundle).
npm run tauri icon path/to/logo.png

npm run tauri:build    # → .exe/.msi (Windows), .dmg (macOS), .AppImage/.deb (Linux)
```

## Prerequisites

- Node 20+
- Rust toolchain (`cargo`) + the Tauri v2 system deps
  (WebView2 on Windows — preinstalled on Windows 11).

## Layout

```
src/                 React app
  api/client.ts      typed backend client (mirrors backend schemas)
  config.ts          persisted server config (localStorage)
  views/             ServerConfig · VoiceLibrary · BatchConvert
src-tauri/           Tauri v2 shell (Rust) → builds the native binary
```
