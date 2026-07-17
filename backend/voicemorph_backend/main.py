"""FastAPI application: REST endpoints + real-time WebSocket streaming.

Job execution is pluggable: eager (in-process background task, dev/tests) or
Celery (production GPU workers). The API and workers share storage and the job
store so results persist and status is consistent.
"""

from __future__ import annotations

import contextlib
import json
from functools import lru_cache
from pathlib import Path

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from voicemorph_engine.backends import get_backend
from voicemorph_engine.backends.base import ConversionParams, StreamConfig
from voicemorph_engine.errors import ProfileNotFoundError, VoiceMorphError

from voicemorph_backend.auth import require_api_key
from voicemorph_backend.jobs import build_job_store
from voicemorph_backend.schemas import JobKind, JobOut, VoiceCreatedOut, VoiceStatusOut
from voicemorph_backend.service import VoiceMorphService
from voicemorph_backend.settings import get_settings
from voicemorph_backend.storage import build_storage
from voicemorph_backend.streaming import (
    StreamSession,
    bytes_to_float32,
    float32_to_bytes,
)


@lru_cache
def get_service() -> VoiceMorphService:
    settings = get_settings()
    return VoiceMorphService(settings, build_storage(settings), build_job_store(settings))


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="VoiceMorph", version="0.1.0", description="Voice conversion backend")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- dispatch: eager (background task) or celery -----------------------

    def _dispatch(bg: BackgroundTasks, fn_name: str, *args) -> None:
        service = get_service()
        method = {"train": "run_training", "convert": "run_conversion"}[fn_name]
        if settings.job_mode == "celery":
            from voicemorph_backend import tasks

            # Celery re-raises so the worker records task failure/retries.
            {"train": tasks.train_task, "convert": tasks.convert_task}[fn_name].delay(*args)
        else:
            # Eager: the job store already records failures; swallow the re-raise
            # so it doesn't bubble out of the background task (job state carries it).
            def _run() -> None:
                with contextlib.suppress(Exception):
                    getattr(service, method)(*args)

            bg.add_task(_run)

    # -- health ------------------------------------------------------------

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "engine_backend": settings.engine_backend,
            "job_mode": settings.job_mode,
        }

    # -- voices ------------------------------------------------------------

    @app.post("/voices", response_model=VoiceCreatedOut, dependencies=[Depends(require_api_key)])
    async def create_voice(
        bg: BackgroundTasks,
        name: str = Form(...),
        consent: str = Form(..., description="JSON consent object; confirmed MUST be true."),
        epochs: int = Form(200),
        files: list[UploadFile] = File(...),
        service: VoiceMorphService = Depends(get_service),
    ) -> VoiceCreatedOut:
        try:
            consent_data = json.loads(consent)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail=f"Invalid consent JSON: {exc}") from exc

        # Stage uploads to a temp dir, then create the (consent-gated) profile.
        tmp = service.engine_config.artifacts_dir / "uploads" / service.new_job_id()
        tmp.mkdir(parents=True, exist_ok=True)
        sample_paths = []
        for f in files:
            dest = tmp / (f.filename or "sample.wav")
            dest.write_bytes(await f.read())
            sample_paths.append(dest)

        try:
            consent_record = service.consent_from_dict(name, consent_data)
            created = service.create_voice(name, consent_record, sample_paths)
        except VoiceMorphError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        job_id = service.new_job_id()
        service.jobs.create(job_id, JobKind.TRAIN, created.voice_id)
        _dispatch(bg, "train", job_id, created.voice_id, epochs)
        return created

    @app.get(
        "/voices/{voice_id}/status",
        response_model=VoiceStatusOut,
        dependencies=[Depends(require_api_key)],
    )
    def voice_status(
        voice_id: str, service: VoiceMorphService = Depends(get_service)
    ) -> VoiceStatusOut:
        try:
            return service.voice_status(voice_id)
        except ProfileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    # -- batch conversion --------------------------------------------------

    @app.post("/convert/batch", response_model=JobOut, dependencies=[Depends(require_api_key)])
    async def convert_batch(
        bg: BackgroundTasks,
        voice_id: str = Form(...),
        transpose: int = Form(0),
        index_rate: float = Form(0.75),
        protect: float = Form(0.33),
        file: UploadFile = File(...),
        service: VoiceMorphService = Depends(get_service),
    ) -> JobOut:
        job_id = service.new_job_id()
        ext = Path(file.filename or "input.wav").suffix or ".wav"
        source_key = f"jobs/{job_id}/input{ext}"
        # Stage upload into storage.
        staged = service.engine_config.artifacts_dir / job_id / f"input{ext}"
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(await file.read())
        service.storage.put_file(source_key, staged)

        params = ConversionParams(transpose=transpose, index_rate=index_rate, protect=protect)
        job = service.jobs.create(job_id, JobKind.CONVERT, voice_id)
        _dispatch(bg, "convert", job_id, voice_id, source_key, ext, params.model_dump())
        return job

    @app.get(
        "/convert/batch/{job_id}",
        response_model=JobOut,
        dependencies=[Depends(require_api_key)],
    )
    def convert_status(
        job_id: str, service: VoiceMorphService = Depends(get_service)
    ) -> JobOut:
        job = service.jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"No job {job_id}")
        return job

    @app.get("/convert/batch/{job_id}/download", dependencies=[Depends(require_api_key)])
    def convert_download(
        job_id: str, service: VoiceMorphService = Depends(get_service)
    ) -> FileResponse:
        job = service.jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"No job {job_id}")
        if job.result_key is None:
            raise HTTPException(
                status_code=409, detail=f"Job {job_id} has no result (state={job.state})."
            )
        path = service.storage.local_path(job.result_key)
        return FileResponse(str(path), filename=Path(job.result_key).name)

    # -- real-time streaming ----------------------------------------------

    @app.websocket("/convert/stream/{voice_id}")
    async def convert_stream(ws: WebSocket, voice_id: str) -> None:
        # API-key via query param or subprotocol header for WS clients.
        key = ws.query_params.get("api_key") or ws.headers.get("x-api-key")
        if key != settings.api_key:
            await ws.close(code=4401)
            return
        await ws.accept()

        service = get_service()
        try:
            profile = service.registry.get(voice_id)
            if not profile.is_ready:
                await ws.close(code=4404)
                return
            backend = get_backend(service.engine_config)
            backend.load_voice(
                voice_id,
                Path(profile.model_path),
                Path(profile.index_path) if profile.index_path else None,
            )
        except VoiceMorphError:
            await ws.close(code=4404)
            return

        cfg = StreamConfig(sample_rate=service.engine_config.sample_rate)
        session = StreamSession(backend, voice_id, ConversionParams(), cfg)
        try:
            while True:
                data = await ws.receive_bytes()
                session.push(bytes_to_float32(data))
                for out in session.drain():
                    await ws.send_bytes(float32_to_bytes(out))
        except WebSocketDisconnect:
            pass
        finally:
            try:
                for out in session.close():
                    await ws.send_bytes(float32_to_bytes(out))
            except Exception:
                pass

    return app


app = create_app()
