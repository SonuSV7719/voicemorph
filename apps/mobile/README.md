# voicemorph-mobile (M7)

React Native (Expo) + TypeScript Android client. A thin client to a VoiceMorph
backend (LAN or cloud) — mobile GPUs can't run conversion, so all heavy work
stays on the server.

## Features (batch mode)

- **Server** — configure backend URL + API key; test connection.
- **Voices** — create a consent-gated profile from picked audio samples; watch
  training status; local library.
- **Convert** — pick an audio/video file, choose a target voice, convert, track
  progress, and save the result to device storage.

Live mic streaming (over the WebSocket, same wire format as
`examples/stream_client.py`) is a later increment.

## Develop

```bash
cd apps/mobile
npm install
npm run typecheck      # tsc --noEmit
npm start              # Expo dev server (scan QR with Expo Go)
npm run android        # build & run on an emulator/device (needs Android SDK)
```

> On an Android emulator the backend host is `http://10.0.2.2:8000`. On a
> physical device use your server's LAN IP.

## Build the APK / AAB

Uses [EAS Build](https://docs.expo.dev/build/introduction/):

```bash
npm install -g eas-cli
eas login
npm run build:apk      # internal-distribution .apk (preview profile)
npm run build:aab      # Play Store .aab (production profile)
```

A local build is also possible with `npx expo run:android --variant release`
given a full Android SDK/NDK toolchain.

## Layout

```
App.tsx              tab shell (Convert · Voices · Server)
src/api/client.ts    typed backend client (RN FormData uploads)
src/config.ts        persisted config + voice list (AsyncStorage)
src/screens/         ServerScreen · VoicesScreen · ConvertScreen
src/theme.ts         shared styles
```
