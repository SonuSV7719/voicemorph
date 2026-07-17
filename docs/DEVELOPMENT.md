# Development guide

## Prerequisites

| Tool | Version | For |
|---|---|---|
| Python | 3.10 / 3.11 (engine ML); 3.13 OK for media/backend | engine, media, backend |
| Node | 20+ | desktop, mobile |
| Rust + cargo | stable | desktop (Tauri) |
| ffmpeg / ffprobe | recent | media layer |
| Docker | 24+ | full stack (optional) |
| NVIDIA GPU + CUDA | — | real RVC conversion (optional) |

## Python packages

```bash
python -m venv .venv && . .venv/Scripts/activate      # Windows: .venv\Scripts\activate
pip install -e "./engine[dev]" -e "./media[dev]" -e "./backend[dev]"

# Full ML stack for real RVC (Python 3.10/3.11 only):
pip install -e "./engine[ml]"
```

Two dependency layers: a light base (numpy/pydantic/typer/fastapi/…) that installs
anywhere, and the engine `[ml]` extra (torch/rvc/faiss) for GPU conversion.

## Run the backend (CPU)

```bash
VOICEMORPH_API_KEY=dev VOICEMORPH_ENGINE_BACKEND=passthrough VOICEMORPH_JOB_MODE=eager \
  uvicorn voicemorph_backend.main:app --reload
```

## Frontends

```bash
cd apps/desktop && npm install && npm run tauri:dev   # desktop (Tauri)
cd apps/mobile  && npm install && npm start           # mobile (Expo)
```

## Tests & linting

```bash
# Python
pytest engine/tests media/tests backend/tests
ruff check engine media backend
mypy engine/voicemorph_engine        # optional, strict

# Frontends
cd apps/desktop && npm run build       # tsc strict + vite
cd apps/mobile  && npm run typecheck
```

CI runs ruff + pytest on Python 3.10 and 3.11 — see
[`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

## Project conventions

- **Line length** 100; `ruff` formatting/lint (`E,F,I,UP,B,SIM`).
- **Engine** stays backend-agnostic: depend only on
  `voicemorph_engine.backends.base`, never a concrete backend. Add a backend by
  implementing `VoiceConversionBackend` and registering it in
  `backends/__init__.py::get_backend`.
- **Third-party RVC calls** live only in `engine/.../backends/_rvc_driver.py`.
- **Duration preservation** is a checked invariant — don't bypass the drift check.
- **Consent gate** must not be weakened (see [ETHICS](./ETHICS.md)).
- Every non-trivial change gets a test; update `CHANGELOG.md` (Unreleased).

## Repo map

See the tree in the [README](../README.md#-architecture) and
[ARCHITECTURE.md](./ARCHITECTURE.md).
