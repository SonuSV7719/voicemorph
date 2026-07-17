# Configuration

All backend settings are environment variables prefixed `VOICEMORPH_` (loaded via
pydantic-settings; a `.env` file in the working directory is also read). See
[`backend/voicemorph_backend/settings.py`](../backend/voicemorph_backend/settings.py)
and [`.env.example`](../.env.example).

## API

| Variable | Default | Description |
|---|---|---|
| `VOICEMORPH_API_KEY` | `change-me` | Shared-secret API key. **Change in production.** |
| `VOICEMORPH_CORS_ORIGINS` | `["*"]` | Allowed CORS origins (JSON list). |
| `VOICEMORPH_MAX_UPLOAD_MB` | `512` | Upload size guidance/limit. |

## Engine

| Variable | Default | Description |
|---|---|---|
| `VOICEMORPH_ENGINE_BACKEND` | `passthrough` | `passthrough` (identity, CPU, dev/CI) or `rvc` (real conversion, GPU). |
| `VOICEMORPH_DEVICE` | `auto` | `auto` \| `cuda` \| `cuda:N` \| `cpu`. |
| `VOICEMORPH_SAMPLE_RATE` | `40000` | Canonical engine sample rate. |

## Jobs

| Variable | Default | Description |
|---|---|---|
| `VOICEMORPH_JOB_MODE` | `eager` | `eager` (in-process, dev/tests) or `celery` (Redis workers, prod). |
| `VOICEMORPH_REDIS_URL` | `redis://localhost:6379/0` | Celery broker/result backend. |

## Storage

| Variable | Default | Description |
|---|---|---|
| `VOICEMORPH_STORAGE_BACKEND` | `local` | `local` (filesystem) or `s3` (S3/MinIO). |
| `VOICEMORPH_STORAGE_ROOT` | `./.voicemorph-data` | Root for local storage + engine data + S3 cache. |
| `VOICEMORPH_S3_ENDPOINT` | `http://localhost:9000` | S3/MinIO endpoint. |
| `VOICEMORPH_S3_ACCESS_KEY` | `minioadmin` | S3 access key. |
| `VOICEMORPH_S3_SECRET_KEY` | `minioadmin` | S3 secret key. |
| `VOICEMORPH_S3_BUCKET` | `voicemorph` | Bucket for models/artifacts. |
| `VOICEMORPH_S3_REGION` | `us-east-1` | S3 region. |

## Engine (CLI / worker) data paths

| Variable | Default | Description |
|---|---|---|
| `VOICEMORPH_HOME` | `~/.voicemorph` | Root for profiles, models, artifacts (engine/CLI). |
| `VOICEMORPH_RVC_TRAIN_CMD` | _(unset)_ | Command template for the RVC training toolchain — see [ENGINE.md](./ENGINE.md). |
| `RMVPE_ROOT` | `<models>/rmvpe` | Where the RMVPE pitch model is found (set by the engine). |

## Common profiles

**Local dev (CPU, no infra):**
```bash
VOICEMORPH_API_KEY=dev
VOICEMORPH_ENGINE_BACKEND=passthrough
VOICEMORPH_JOB_MODE=eager
VOICEMORPH_STORAGE_BACKEND=local
```

**Production (GPU workers):**
```bash
VOICEMORPH_API_KEY=<strong-secret>
VOICEMORPH_ENGINE_BACKEND=rvc
VOICEMORPH_DEVICE=cuda:0
VOICEMORPH_JOB_MODE=celery
VOICEMORPH_REDIS_URL=redis://redis:6379/0
VOICEMORPH_STORAGE_BACKEND=s3
VOICEMORPH_S3_ENDPOINT=http://minio:9000
```

## Client configuration

- **Desktop:** set backend URL + API key in the **Server** tab (persisted in
  `localStorage`).
- **Mobile:** set them in the **Server** screen (persisted via AsyncStorage). On
  the Android emulator, reach a host-machine backend at `http://10.0.2.2:8000`.
