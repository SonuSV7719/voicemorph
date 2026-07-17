"""Core service operations shared by the API and the Celery workers.

Bridges the HTTP layer to the engine + media layers and to storage/jobs. The
same code path runs whether jobs execute eagerly (dev) or on a worker (prod).
"""

from __future__ import annotations

import uuid
from pathlib import Path

from voicemorph_engine.backends import get_backend
from voicemorph_engine.backends.base import ConversionParams, TrainingParams
from voicemorph_engine.config import EngineConfig
from voicemorph_engine.profiles import ConsentMethod, ConsentRecord, ProfileRegistry, ProfileStatus
from voicemorph_media.pipeline import convert_media

from voicemorph_backend.jobs import JobStore
from voicemorph_backend.schemas import JobState, VoiceCreatedOut, VoiceStatusOut
from voicemorph_backend.settings import Settings
from voicemorph_backend.storage import Storage


class VoiceMorphService:
    def __init__(self, settings: Settings, storage: Storage, jobs: JobStore):
        self.settings = settings
        self.storage = storage
        self.jobs = jobs
        self.engine_config = EngineConfig(
            root=settings.storage_root / "engine",
            device=settings.device,
            backend=settings.engine_backend,
            sample_rate=settings.sample_rate,
        )
        self.engine_config.ensure_dirs()
        self.registry = ProfileRegistry(self.engine_config.profiles_dir)

    # -- voices -------------------------------------------------------------

    def create_voice(
        self, name: str, consent: ConsentRecord, sample_paths: list[Path]
    ) -> VoiceCreatedOut:
        """Create a profile (consent-gated) and stage its raw samples."""
        profile = self.registry.create(
            name=name,
            consent=consent,
            backend=self.engine_config.backend,
            sample_rate=self.engine_config.sample_rate,
        )
        raw_dir = self.registry.profile_dir(profile.voice_id) / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        for i, sp in enumerate(sample_paths):
            (raw_dir / f"sample_{i:03d}{Path(sp).suffix or '.wav'}").write_bytes(
                Path(sp).read_bytes()
            )
        return VoiceCreatedOut(
            voice_id=profile.voice_id, name=profile.name, status=profile.status.value
        )

    def voice_status(self, voice_id: str) -> VoiceStatusOut:
        p = self.registry.get(voice_id)
        return VoiceStatusOut(
            voice_id=p.voice_id,
            name=p.name,
            status=p.status.value,
            ready=p.is_ready,
            error=p.error,
            dataset_seconds=p.metadata.get("dataset_seconds"),
        )

    @staticmethod
    def consent_from_dict(name_subject: str, data: dict) -> ConsentRecord:
        return ConsentRecord(
            subject=data["subject"],
            granted_by=data.get("granted_by") or data["subject"],
            method=ConsentMethod(data.get("method", "self")),
            reference=data.get("reference"),
            confirmed=bool(data.get("confirmed", False)),
        )

    # -- training job -------------------------------------------------------

    def run_training(self, job_id: str, voice_id: str, epochs: int = 200) -> None:
        from voicemorph_engine.preprocessing import preprocess_dataset

        self.jobs.update(job_id, state=JobState.RUNNING, progress=0.05, message="preprocessing")
        profile = self.registry.get(voice_id)
        pdir = self.registry.profile_dir(voice_id)
        try:
            profile.status = ProfileStatus.PREPROCESSING
            self.registry.save(profile)
            report = preprocess_dataset(pdir / "raw", pdir / "dataset")
            profile.metadata["dataset_seconds"] = round(report.total_seconds, 2)
            profile.status = ProfileStatus.TRAINING
            self.registry.save(profile)

            self.jobs.update(job_id, progress=0.2, message="training")
            backend = get_backend(self.engine_config)
            result = backend.train(
                voice_id=voice_id,
                dataset_dir=pdir / "dataset",
                output_dir=pdir,
                params=TrainingParams(epochs=epochs, sample_rate=self.engine_config.sample_rate),
            )
            profile.status = ProfileStatus.READY
            profile.model_path = result.model_path
            profile.index_path = result.index_path
            profile.error = None
            self.registry.save(profile)

            # Persist model artifacts to shared storage.
            self.storage.put_file(f"voices/{voice_id}/model.pth", Path(result.model_path))
            if result.index_path:
                self.storage.put_file(f"voices/{voice_id}/model.index", Path(result.index_path))

            self.jobs.update(job_id, state=JobState.SUCCEEDED, progress=1.0, message="ready")
        except Exception as exc:
            profile.status = ProfileStatus.FAILED
            profile.error = str(exc)
            self.registry.save(profile)
            self.jobs.update(job_id, state=JobState.FAILED, error=str(exc))
            raise

    # -- conversion job -----------------------------------------------------

    def run_conversion(
        self, job_id: str, voice_id: str, source_key: str, output_ext: str, params: ConversionParams
    ) -> None:
        self.jobs.update(job_id, state=JobState.RUNNING, progress=0.1, message="loading voice")
        try:
            profile = self.registry.get(voice_id)
            if not profile.is_ready:
                raise RuntimeError(
                    f"Voice {voice_id} is not trained (status={profile.status.value})."
                )

            backend = get_backend(self.engine_config)
            backend.load_voice(
                voice_id,
                Path(profile.model_path),
                Path(profile.index_path) if profile.index_path else None,
            )

            work = self.engine_config.artifacts_dir / job_id
            work.mkdir(parents=True, exist_ok=True)
            source = self.storage.local_path(source_key)
            output = work / f"output{output_ext}"

            self.jobs.update(job_id, progress=0.4, message="converting")
            result = convert_media(
                source=source,
                output=output,
                convert_audio=lambda a, o: backend.convert_file(voice_id, a, o, params),
                work_dir=work,
                sample_rate=self.engine_config.sample_rate,
            )

            result_key = f"jobs/{job_id}/output{output_ext}"
            self.storage.put_file(result_key, output)
            self.jobs.update(
                job_id,
                state=JobState.SUCCEEDED,
                progress=1.0,
                message="done",
                result_key=result_key,
                output_kind=result.kind,
            )
        except Exception as exc:
            self.jobs.update(job_id, state=JobState.FAILED, error=str(exc))
            raise

    @staticmethod
    def new_job_id() -> str:
        return uuid.uuid4().hex
