"""Celery tasks — thin wrappers that build a service and delegate to it.

Building the service inside the task (not at import) keeps the worker's engine
backend (GPU RVC) and storage consistent with its own environment.
"""

from __future__ import annotations

from voicemorph_engine.backends.base import ConversionParams

from voicemorph_backend.celery_app import celery_app
from voicemorph_backend.jobs import build_job_store
from voicemorph_backend.service import VoiceMorphService
from voicemorph_backend.settings import get_settings
from voicemorph_backend.storage import build_storage


def _service() -> VoiceMorphService:
    settings = get_settings()
    return VoiceMorphService(settings, build_storage(settings), build_job_store(settings))


@celery_app.task(name="voicemorph.train")
def train_task(job_id: str, voice_id: str, epochs: int = 200) -> None:
    _service().run_training(job_id, voice_id, epochs=epochs)


@celery_app.task(name="voicemorph.convert")
def convert_task(
    job_id: str, voice_id: str, source_key: str, output_ext: str, params: dict
) -> None:
    _service().run_conversion(
        job_id, voice_id, source_key, output_ext, ConversionParams(**params)
    )
