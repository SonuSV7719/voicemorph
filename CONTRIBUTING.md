# Contributing to VoiceMorph

Thanks for helping build VoiceMorph. A few ground rules keep the project healthy.
By participating you agree to our [Code of Conduct](CODE_OF_CONDUCT.md). For the
full developer setup see [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).

## Ethics first

VoiceMorph is consent-first (see [`docs/ETHICS.md`](docs/ETHICS.md)). Do not
submit changes that remove or weaken the consent gate, add a TTS/dialogue-
fabrication path, or facilitate impersonation or auth-bypass.

## Monorepo layout

See [`README.md`](README.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
Each Python package (`engine/`, `media/`) installs independently.

## Dev setup

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -e "./engine[dev]" -e "./media[dev]"
```

The engine's heavy ML stack lives in the `[ml]` extra and needs Python 3.10/3.11
+ a CUDA GPU; the base install (and CI) runs without it.

## Before you push

```bash
ruff check engine media
pytest engine/tests media/tests
```

## Commits & PRs

- Small, focused commits. Conventional-commit-style messages are welcome.
- Every non-trivial change to the engine or media layer needs a test.
- CI (lint + tests on Python 3.10/3.11) must pass.
