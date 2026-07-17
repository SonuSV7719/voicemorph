# GPU worker image — runs Celery training/inference tasks with the full RVC/ML
# stack. Requires an NVIDIA GPU + the NVIDIA Container Toolkit on the host.
FROM nvidia/cuda:13.3.0-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3.11 python3-pip ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY engine /app/engine
COPY media /app/media
COPY backend /app/backend

# Install with the engine ML extra (torch/rvc/faiss) for real conversion.
RUN pip install --no-cache-dir "./engine[ml]" ./media ./backend

ENV VOICEMORPH_JOB_MODE=celery \
    VOICEMORPH_STORAGE_BACKEND=s3 \
    VOICEMORPH_ENGINE_BACKEND=rvc \
    VOICEMORPH_DEVICE=cuda:0

# Model weights (RMVPE + pretrained bases) should be mounted or baked at
# $VOICEMORPH_HOME/models — see docs/ENGINE.md.
CMD ["celery", "-A", "voicemorph_backend.celery_app.celery_app", "worker", \
     "--loglevel=info", "--concurrency=1"]
