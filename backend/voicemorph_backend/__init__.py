"""VoiceMorph backend service.

FastAPI REST + WebSocket API in front of the engine and media layers, with a
Celery/Redis job queue and S3/MinIO object storage. Runs on CPU for development
(local storage + eager job execution + the ``passthrough`` engine backend) and
scales out to GPU workers in production.
"""

from __future__ import annotations

__version__ = "0.1.0"
