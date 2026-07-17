# Release & distribution (M8)

Tagging a version (`vX.Y.Z`) triggers the release workflows.

```bash
git tag v0.1.0
git push origin v0.1.0
```

## Desktop (`.exe`/`.msi`, `.dmg`, `.AppImage`/`.deb`)

Workflow: [`.github/workflows/release-desktop.yml`](../.github/workflows/release-desktop.yml)
(builds via `tauri-action` on Windows/macOS/Linux and attaches artifacts to a
**draft** GitHub Release).

**Prerequisites**

- App icons under `apps/desktop/src-tauri/icons/` (generate once:
  `cd apps/desktop && npm run tauri icon path/to/logo-1024.png`).

**Optional code signing** (set as repo secrets to enable; unsigned builds work
without them):

| Secret | Purpose |
|---|---|
| `TAURI_SIGNING_PRIVATE_KEY` | Tauri updater signing key |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | its password |

For OS-level signing: Windows Authenticode (EV cert) and Apple Developer ID +
notarization — add the standard Tauri signing env vars when you have certs.

## Mobile (Android `.apk` / `.aab`)

Workflow: [`.github/workflows/release-mobile.yml`](../.github/workflows/release-mobile.yml)
(Expo EAS). Config: [`apps/mobile/eas.json`](../apps/mobile/eas.json).

- `preview` profile → installable **APK** (internal distribution).
- `production` profile → **AAB** for Play Store, with `autoIncrement` version code.

**Prerequisites**

| Secret | Purpose |
|---|---|
| `EXPO_TOKEN` | Expo access token (EAS auth) |

Android signing keystores are managed by EAS (`eas credentials`) or supplied via
`eas.json`. First run: `cd apps/mobile && eas build:configure`.

## Backend images

The API and GPU worker images build from [`docker/`](../docker). Publish them to
your registry in a separate deploy pipeline (out of scope for the app release
workflows above).

## Versioning

Keep these in lockstep with the tag:

- `apps/desktop/src-tauri/tauri.conf.json` → `version`
- `apps/desktop/package.json` → `version`
- `apps/mobile/app.json` → `expo.version` (and bump `android.versionCode`)
- engine/media/backend `pyproject.toml` → `version`
