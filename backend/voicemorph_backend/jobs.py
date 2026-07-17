"""Job store: tracks training/conversion job state.

Two implementations behind one interface:

* :class:`MemoryJobStore` — process-local dict (dev/tests, eager mode).
* :class:`RedisJobStore` — shared across API + Celery workers (production).
"""

from __future__ import annotations

import abc
import threading

from voicemorph_backend.schemas import JobKind, JobOut, JobState


class JobStore(abc.ABC):
    @abc.abstractmethod
    def create(self, job_id: str, kind: JobKind, voice_id: str | None) -> JobOut: ...

    @abc.abstractmethod
    def get(self, job_id: str) -> JobOut | None: ...

    @abc.abstractmethod
    def update(self, job_id: str, **fields) -> JobOut: ...


class MemoryJobStore(JobStore):
    def __init__(self) -> None:
        self._jobs: dict[str, JobOut] = {}
        self._lock = threading.Lock()

    def create(self, job_id: str, kind: JobKind, voice_id: str | None) -> JobOut:
        job = JobOut(job_id=job_id, kind=kind, state=JobState.QUEUED, voice_id=voice_id)
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> JobOut | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **fields) -> JobOut:
        with self._lock:
            job = self._jobs[job_id]
            updated = job.model_copy(update=fields)
            self._jobs[job_id] = updated
            return updated


class RedisJobStore(JobStore):
    """Redis-backed store; jobs are JSON blobs keyed by ``job:<id>``."""

    def __init__(self, redis_url: str, ttl_seconds: int = 7 * 24 * 3600) -> None:
        import redis

        self._r = redis.Redis.from_url(redis_url, decode_responses=True)
        self._ttl = ttl_seconds

    def _key(self, job_id: str) -> str:
        return f"job:{job_id}"

    def create(self, job_id: str, kind: JobKind, voice_id: str | None) -> JobOut:
        job = JobOut(job_id=job_id, kind=kind, state=JobState.QUEUED, voice_id=voice_id)
        self._r.set(self._key(job_id), job.model_dump_json(), ex=self._ttl)
        return job

    def get(self, job_id: str) -> JobOut | None:
        raw = self._r.get(self._key(job_id))
        return JobOut.model_validate_json(raw) if raw else None

    def update(self, job_id: str, **fields) -> JobOut:
        raw = self._r.get(self._key(job_id))
        if raw is None:
            raise KeyError(job_id)
        job = JobOut.model_validate_json(raw).model_copy(update=fields)
        self._r.set(self._key(job_id), job.model_dump_json(), ex=self._ttl)
        return job


def build_job_store(settings) -> JobStore:
    if settings.job_mode == "celery":
        return RedisJobStore(settings.redis_url)
    return MemoryJobStore()
