# apps

Native clients. Both are thin clients to the VoiceMorph backend (the desktop app
may optionally bundle a local server when a GPU is present).

- **desktop/** — Tauri v2 + React/TS → `.exe` / `.dmg` / `.AppImage`. ✅ batch mode
  (voice-profile library, drag-and-drop convert, server config). Live mic mode
  with virtual-audio-device routing is M6.
- **mobile/** — React Native (Expo) + TS → `.apk` / `.aab`. ✅ batch mode
  (consent-gated profiles, pick audio/video, convert, save to device, server
  config). Live mode over WebSocket is a later increment.

Both are thin clients to the backend and share the same typed API-client shape.
