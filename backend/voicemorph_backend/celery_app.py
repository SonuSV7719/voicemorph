"""Celery application for background training/conversion jobs (production).

In dev/tests the API uses eager execution and never touches this. When
``VOICEMORPH_JOB_MODE=celery``, the API dispatches to these tasks and the worker
(the GPU image) executes them.
"""

from __future__ import annotations

from celery import Celery

from voicemorph_backend.settings import get_settings

_settings = get_settings()

celery_app = Celery(
    "voicemorph",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,   # fair dispatch for long GPU jobs
    task_acks_late=True,
)

# Import tasks so they register with the app.
from voicemorph_backend import tasks  # noqa: E402,F401
