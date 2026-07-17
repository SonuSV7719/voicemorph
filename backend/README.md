# voicemorph-backend (M3)

FastAPI REST + WebSocket API in front of the engine and media layers, with a
Celery/Redis job queue and S3/MinIO object storage.

## Modes

The backend runs two ways from the same code:

| | Dev / CI (default) | Production |
|---|---|---|
| Engine backend | `passthrough` (identity, CPU) | `rvc` (GPU) |
| Jobs | `eager` (in-process) | `celery` (Redis broker) |
| Storage | `local` (filesystem) | `s3` (MinIO/S3) |

Configure via `VOICEMORPH_*` env vars (see [`settings.py`](voicemorph_backend/settings.py)).

## Run locally (CPU, no broker)

```bash
pip install -e "./engine" -e "./media" -e "./backend[dev]"
VOICEMORPH_API_KEY=dev VOICEMORPH_ENGINE_BACKEND=passthrough VOICEMORPH_JOB_MODE=eager \
  uvicorn voicemorph_backend.main:app --reload
```

## Run the full stack (Docker)

```bash
docker compose -f docker/docker-compose.yml up --build
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET  | `/health` | liveness + active backend/job mode |
| POST | `/voices` | multipart: `name`, `consent` (JSON, `confirmed` must be true), `files[]` → creates a **consent-gated** profile and starts training; returns `voice_id` |
| GET  | `/voices/{voice_id}/status` | training progress / readiness |
| POST | `/convert/batch` | multipart: `voice_id`, `file`, params → enqueue conversion; returns `job_id` |
| GET  | `/convert/batch/{job_id}` | poll job state |
| GET  | `/convert/batch/{job_id}/download` | download the converted result |
| WS   | `/convert/stream/{voice_id}` | real-time streaming (float32 mono PCM in/out); auth via `?api_key=` |

Auth: `X-API-Key` header (or `Authorization: Bearer <key>`).

## Tests

```bash
pytest backend/tests    # full create→train→convert→download flow on CPU
```
