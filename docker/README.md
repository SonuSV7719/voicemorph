# docker (milestone M3)

- `inference.Dockerfile` — GPU-enabled image (CUDA + torch + RVC) for the Celery
  training/inference workers.
- `api.Dockerfile` — lightweight image for the FastAPI API layer.
- `docker-compose.yml` — local stack: api + worker (GPU) + redis + minio.

Added when the backend service lands.
