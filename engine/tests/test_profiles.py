"""Consent-gate and registry behavior."""

from __future__ import annotations

import pytest

from voicemorph_engine.errors import ConsentRequiredError, ProfileNotFoundError
from voicemorph_engine.profiles import ConsentMethod, ConsentRecord, ProfileRegistry


def test_training_refused_without_confirmed_consent(tmp_path):
    reg = ProfileRegistry(tmp_path / "profiles")
    consent = ConsentRecord(subject="Alex", granted_by="Alex", confirmed=False)
    with pytest.raises(ConsentRequiredError):
        reg.create(name="Alex", consent=consent)


def test_profile_roundtrip(tmp_path):
    reg = ProfileRegistry(tmp_path / "profiles")
    consent = ConsentRecord(
        subject="Alex", granted_by="Alex", method=ConsentMethod.SELF, confirmed=True
    )
    profile = reg.create(name="Alex", consent=consent)
    assert reg.exists(profile.voice_id)

    fetched = reg.get(profile.voice_id)
    assert fetched.name == "Alex"
    assert fetched.consent.confirmed is True
    assert not fetched.is_ready  # not trained yet

    assert [p.voice_id for p in reg.list()] == [profile.voice_id]

    reg.delete(profile.voice_id)
    assert not reg.exists(profile.voice_id)
    with pytest.raises(ProfileNotFoundError):
        reg.get(profile.voice_id)


def test_consent_requires_named_subject(tmp_path):
    reg = ProfileRegistry(tmp_path / "profiles")
    consent = ConsentRecord(subject="  ", granted_by="Alex", confirmed=True)
    with pytest.raises(ConsentRequiredError):
        reg.create(name="x", consent=consent)
