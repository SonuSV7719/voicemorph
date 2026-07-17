# apps

Native clients. Both are thin clients to the VoiceMorph backend (the desktop app
may optionally bundle a local server when a GPU is present).

- **desktop/** (M4/M6) — Tauri + React/TS → `.exe` / `.dmg` / `.AppImage`.
  Voice-profile library, drag-and-drop batch convert, live mic mode with virtual
  audio device routing, server-config screen.
- **mobile/** (M7) — React Native → `.apk` / `.aab`. Record/import target, batch
  convert, save result; optional live mode over WebSocket; server-config screen.

Scaffolded once the backend API is stable (M3).
