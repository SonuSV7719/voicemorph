# backend (milestone M3)

FastAPI service + Celery/Redis job queue + MinIO/S3 storage. Placeholder until
the engine batch path is proven on the CLI (M1) and the media round-trip is
verified (M2).

Planned endpoints:

| Method | Path | Purpose |
|---|---|---|
| POST | `/voices` | upload target sample(s) + consent → train, returns `voice_id` |
| GET  | `/voices/{voice_id}/status` | training progress |
| POST | `/convert/batch` | upload source + `voice_id` → enqueue job, returns `job_id` |
| GET  | `/convert/batch/{job_id}` | poll status / download result |
| WS   | `/convert/stream/{voice_id}` | real-time streaming conversion |

Auth: API-key/token. See [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).
