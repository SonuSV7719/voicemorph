# Security Policy

## Supported versions

VoiceMorph is pre-1.0 and under active development. Security fixes are applied to
the latest `main` and the most recent tagged release.

| Version | Supported |
|---|---|
| `main` (latest) | ✅ |
| latest `vX.Y.Z` tag | ✅ |
| older tags | ❌ |

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Report privately via one of:

1. **GitHub Security Advisories** — [open a draft advisory](https://github.com/SonuSV7719/voicemorph/security/advisories/new)
   (preferred).
2. **Email** — **sonuportfolio77@gmail.com** with subject `VoiceMorph security`.

Please include:

- A description of the vulnerability and its impact.
- Steps to reproduce (proof-of-concept if possible).
- Affected component (engine / media / backend / desktop / mobile) and version/commit.

**Response targets:** acknowledgement within 3 business days; triage and a
remediation plan within 10 business days. We will keep you informed and credit
you in the advisory unless you prefer to remain anonymous.

## Scope & hardening notes

Because VoiceMorph processes uploaded media and hosts an inference API, take note:

- **Authentication** — the backend uses a shared API key. Set a strong
  `VOICEMORPH_API_KEY`; never ship the default `change-me` to production. Terminate
  TLS in front of the API (reverse proxy) — the API key is a bearer secret.
- **Untrusted media** — inputs are passed to `ffmpeg`. Keep `ffmpeg` patched and
  run workers with least privilege; consider sandboxing/containment for the
  conversion workers.
- **Storage** — MinIO/S3 credentials and buckets should not be world-readable.
- **Resource limits** — enforce upload size (`VOICEMORPH_MAX_UPLOAD_MB`) and queue
  backpressure to mitigate DoS via large/expensive jobs.
- **Model artifacts** — treat `.pth`/`.index` files as untrusted if sourced
  externally; only load models you produced or trust.

## Responsible-use reporting

To report **misuse** of a VoiceMorph deployment (non-consensual cloning,
impersonation, fraud), see [`docs/ETHICS.md`](./docs/ETHICS.md). This is distinct
from software vulnerabilities but equally welcome.
