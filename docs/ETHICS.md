# Ethical use & guardrails

VoiceMorph is a **consent-first** voice-conversion tool. These guardrails are part of the product, not an afterthought.

## Core rules

1. **Consent is mandatory.** A target voice profile may only be created from your own voice, or a voice for which you hold explicit, documented consent. The engine refuses to train a profile unless a consent record is attached (`profiles.ConsentRecord`).
2. **No fabrication.** VoiceMorph converts *existing* spoken audio. It never generates new dialogue. There is no TTS fallback.
3. **No impersonation for deception.** Do not use VoiceMorph to defraud, deceive, harass, or to bypass voice-authentication / identity-verification systems.
4. **Legal compliance.** You are responsible for compliance with local laws on synthetic media, likeness/publicity rights, and biometric data (e.g. BIPA, GDPR).

## How the product enforces this

- **Consent gate at profile creation**: `POST /voices` and the engine training entrypoint require a `consent` object (who consented, relationship, timestamp, method). Training aborts with a clear error otherwise.
- **Provenance metadata**: every output can be tagged with a machine-readable marker indicating it is AI voice-converted (recommended; configurable) to support downstream disclosure.
- **Audit log**: profile creation and conversions are logged with the responsible API key.

## Legitimate uses we build for

Dubbing/localization, accessibility (voice banking, assistive voices), audiobook/podcast production with consented talent, film/game post-production, and personal creative projects using your own voice.

## Reporting misuse

If you believe a deployment is being misused, open a private security advisory on the repository.
