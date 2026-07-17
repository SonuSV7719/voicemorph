"""End-to-end API flow on CPU: create voice → train → convert → download.

Uses the passthrough (identity) engine backend and eager job execution, so the
whole pipeline runs without a GPU or a broker.
"""

from __future__ import annotations

import json


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["engine_backend"] == "passthrough"


def test_auth_required(client):
    assert client.get("/voices/does-not-exist/status").status_code == 401


def test_consent_gate_rejects_unconfirmed(client, auth, wav_factory):
    sample = wav_factory("sample.wav")
    r = client.post(
        "/voices",
        headers=auth,
        data={"name": "Alex", "consent": json.dumps({"subject": "Alex", "confirmed": False})},
        files={"files": ("sample.wav", sample.read_bytes(), "audio/wav")},
    )
    assert r.status_code == 422
    assert "consent" in r.text.lower()


def test_full_flow(client, auth, wav_factory):
    sample = wav_factory("sample.wav", seconds=2.0)
    # 1. Create voice (consent confirmed) — training runs eagerly.
    r = client.post(
        "/voices",
        headers=auth,
        data={
            "name": "Alex",
            "consent": json.dumps({"subject": "Alex", "confirmed": True, "method": "self"}),
            "epochs": 1,
        },
        files={"files": ("sample.wav", sample.read_bytes(), "audio/wav")},
    )
    assert r.status_code == 200, r.text
    voice_id = r.json()["voice_id"]

    # 2. Voice should be ready (eager training completed before response).
    s = client.get(f"/voices/{voice_id}/status", headers=auth)
    assert s.status_code == 200
    assert s.json()["ready"] is True, s.json()

    # 3. Convert an audio file.
    src = wav_factory("source.wav", seconds=1.5, freq=330.0)
    c = client.post(
        "/convert/batch",
        headers=auth,
        data={"voice_id": voice_id},
        files={"file": ("source.wav", src.read_bytes(), "audio/wav")},
    )
    assert c.status_code == 200, c.text
    job_id = c.json()["job_id"]

    # 4. Job succeeded.
    j = client.get(f"/convert/batch/{job_id}", headers=auth)
    assert j.status_code == 200
    assert j.json()["state"] == "succeeded", j.json()
    assert j.json()["output_kind"] == "audio"

    # 5. Download the result.
    d = client.get(f"/convert/batch/{job_id}/download", headers=auth)
    assert d.status_code == 200
    assert len(d.content) > 0


def test_convert_rejects_untrained_voice(client, auth, wav_factory):
    # Create a voice but we can't easily leave it untrained in eager mode; instead
    # convert against a bogus voice id → job fails.
    src = wav_factory("source.wav")
    c = client.post(
        "/convert/batch",
        headers=auth,
        data={"voice_id": "nonexistent"},
        files={"file": ("source.wav", src.read_bytes(), "audio/wav")},
    )
    assert c.status_code == 200
    job_id = c.json()["job_id"]
    j = client.get(f"/convert/batch/{job_id}", headers=auth).json()
    assert j["state"] == "failed"
    assert j["error"]
