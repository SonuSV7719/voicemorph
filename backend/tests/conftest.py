"""Test fixtures: a TestClient wired to passthrough backend + eager jobs + local storage."""

from __future__ import annotations

import numpy as np
import pytest
import soundfile as sf


@pytest.fixture
def wav_factory(tmp_path):
    def _make(name: str, seconds: float = 1.0, freq: float = 440.0, sr: int = 16_000):
        t = np.linspace(0.0, seconds, int(seconds * sr), endpoint=False)
        data = (0.4 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
        path = tmp_path / name
        sf.write(str(path), data, sr)
        return path

    return _make


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VOICEMORPH_API_KEY", "test-key")
    monkeypatch.setenv("VOICEMORPH_ENGINE_BACKEND", "passthrough")
    monkeypatch.setenv("VOICEMORPH_JOB_MODE", "eager")
    monkeypatch.setenv("VOICEMORPH_STORAGE_BACKEND", "local")
    monkeypatch.setenv("VOICEMORPH_STORAGE_ROOT", str(tmp_path / "data"))

    from fastapi.testclient import TestClient

    from voicemorph_backend.main import create_app, get_service
    from voicemorph_backend.settings import get_settings

    get_settings.cache_clear()
    get_service.cache_clear()
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth():
    return {"X-API-Key": "test-key"}
