# FAQ

### Is this text-to-speech?

No. VoiceMorph is **voice conversion** — it converts the *timbre* of real spoken
audio while preserving the original words, timing, and emotional delivery. There
is no transcription or re-synthesis step, and no TTS fallback.

### Can it run fully offline on a phone?

No — and we won't fake it. Production-quality real-time conversion is GPU-bound.
The Android app is a **thin client** to a backend (LAN or cloud). The desktop app
can optionally bundle a local server when the machine has a GPU.

### Do I need a GPU?

For **real** conversion, yes (NVIDIA + CUDA, Python 3.10/3.11 for the engine ML
extra). For **development**, no: the `passthrough` backend runs the whole
pipeline on CPU (it performs no conversion — identity audio).

### Why does training need consent, and can I skip it?

Consent is a product requirement. The engine refuses to create a profile without
a confirmed consent record. Please don't try to remove the gate — see
[ETHICS.md](./ETHICS.md). Use only your own voice or one you have documented
rights to.

### How much audio to train a voice?

10–30 minutes of clean, single-speaker audio is a good target. More clean data
generally helps; noisy data hurts.

### What happens to a video's picture?

Nothing. The audio track is extracted, converted, and remuxed back in with the
**video stream copied bit-identical** (`-c:v copy`); subtitles/metadata are
preserved. Only the voice changes.

### The output has to line up with the original — is timing guaranteed?

Duration preservation is a **checked invariant**: batch conversion fails loudly
if the output duration drifts beyond tolerance from the source.

### What's the streaming latency?

Target ≤ ~300 ms end-to-end on a consumer GPU, plus network time for remote
servers. The wire format is little-endian float32 mono PCM at 40 kHz.

### Which model does it use?

RVC (Retrieval-based Voice Conversion) with RMVPE pitch estimation. The engine is
backend-agnostic, so other converters can be added behind the same interface.

### How do I build the `.exe` / `.apk`?

See [RELEASE.md](./RELEASE.md). Desktop uses `tauri-action`; Android uses Expo
EAS. Both are wired as tag-triggered GitHub Actions.

### Where are models and jobs stored?

Locally under `~/.voicemorph` (or `VOICEMORPH_HOME`) for the engine/CLI; in
S3/MinIO for the backend. See [CONFIGURATION.md](./CONFIGURATION.md).

### How do I report misuse or a security issue?

Misuse → [ETHICS.md](./ETHICS.md). Vulnerabilities → [SECURITY.md](../SECURITY.md)
(please report privately).
