# Lightweight API image — no GPU, no ML stack. Serves REST + WebSocket and
# dispatches heavy work to the GPU worker via Celery.
FROM python:3.11-slim

# ffmpeg is needed by the media layer (extract/remux).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the three Python packages (engine base deps only — no [ml]).
COPY engine /app/engine
COPY media /app/media
COPY backend /app/backend
RUN pip install --no-cache-dir ./engine ./media ./backend

ENV VOICEMORPH_JOB_MODE=celery \
    VOICEMORPH_STORAGE_BACKEND=s3

EXPOSE 8000
CMD ["uvicorn", "voicemorph_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
