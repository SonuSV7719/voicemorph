# voicemorph-engine

Core voice-conversion engine: per-target-voice RVC training, batch inference
(duration-preserving), and chunked real-time streaming. Backend-agnostic via
`voicemorph_engine.backends.base.VoiceConversionBackend`.

## Install

```bash
python -m venv .venv && . .venv/Scripts/activate    # Windows
pip install -e ".[dev]"          # light deps: import + preprocessing + CLI skeleton
pip install -e ".[ml,dev]"       # full RVC stack (use Python 3.10/3.11)
```

## CLI

```bash
voicemorph profile create --name "Alex" --subject "Alex" --self --confirm
voicemorph preprocess ./raw_alex_audio <voice_id>
voicemorph train <voice_id> --epochs 200
voicemorph convert <voice_id> input.mp4 output.mp4
```

See [`../docs/ENGINE.md`](../docs/ENGINE.md) for weights, training configuration,
and the streaming design.
