"""Hardware detection + auto backend/device selection."""

from __future__ import annotations

from voicemorph_engine import hardware


def test_manual_device_override_is_respected():
    assert hardware.detect_device("cpu") == "cpu"
    assert hardware.detect_device("cuda:1") == "cuda:1"


def test_auto_device_follows_cuda(monkeypatch):
    monkeypatch.setattr(hardware, "has_cuda", lambda: True)
    assert hardware.detect_device("auto") == "cuda:0"
    monkeypatch.setattr(hardware, "has_cuda", lambda: False)
    assert hardware.detect_device("auto") == "cpu"


def test_recommend_prefers_rvc_on_gpu(monkeypatch):
    monkeypatch.setattr(hardware, "backend_available", lambda b: True)
    assert hardware.recommend_backend("cuda:0") == "rvc"


def test_recommend_skips_rvc_on_cpu(monkeypatch):
    # On CPU, rvc is skipped even if importable; next available wins.
    avail = {"rvc", "speecht5", "passthrough"}
    monkeypatch.setattr(hardware, "backend_available", lambda b: b in avail)
    assert hardware.recommend_backend("cpu") == "speecht5"


def test_recommend_falls_back_to_passthrough(monkeypatch):
    monkeypatch.setattr(hardware, "backend_available", lambda b: b == "passthrough")
    assert hardware.recommend_backend("cpu") == "passthrough"
    assert hardware.recommend_backend("cuda:0") == "passthrough"


def test_probe_shape(monkeypatch):
    monkeypatch.setattr(hardware, "has_cuda", lambda: False)
    monkeypatch.setattr(hardware, "gpu_name", lambda: None)
    monkeypatch.setattr(hardware, "backend_available", lambda b: b in {"speecht5", "passthrough"})
    info = hardware.probe("auto")
    assert info.device == "cpu"
    assert info.cuda is False
    assert info.recommended_backend == "speecht5"
    assert "passthrough" in info.available_backends
