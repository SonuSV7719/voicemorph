# Engine guide

## Dependency layers

The engine installs in two layers so the package (and the media/CLI skeleton)
imports on any interpreter:

- **base** — numpy, soundfile, pydantic, typer. Enough for profiles,
  preprocessing, and the CLI skeleton.
- **`[ml]`** — torch, torchaudio, librosa, faiss, `rvc-python`. Required for
  actual training/inference. **Use Python 3.10 or 3.11** and a CUDA-capable GPU.

```bash
pip install "voicemorph-engine[ml]"
```

## Model weights

Place weights under the engine data root (`$VOICEMORPH_HOME`, default
`~/.voicemorph`):

```
~/.voicemorph/models/
├── pretrained/   # RVC pretrained base models (Gxxx/Dxxx)
└── rmvpe/        # rmvpe.pt (pitch estimator)
```

RMVPE is the default pitch estimator (`pitch_method="rmvpe"`) — current
best-practice for RVC pipelines.

## Training

Inference is provided by `rvc-python`. **Training** uses the RVC-Project training
scripts, driven via a command template so we don't fork the training code:

```bash
export VOICEMORPH_RVC_TRAIN_CMD='python infer-web.py --train \
  --exp {voice_id} --dataset {dataset} --sr {sr} --f0method {pitch} \
  --epochs {epochs} --batch {batch_size} --device {device} --outdir {output}'
```

Placeholders: `{dataset} {output} {voice_id} {device} {epochs} {batch_size} {sr} {pitch}`.
`run_training` then discovers the produced `.pth`/`.index` in `{output}`.

10–30 minutes of clean target-voice audio is the recommended dataset size.

## Duration & timing preservation

`convert_file` compares output vs source duration and raises
`DurationMismatchError` beyond `DURATION_TOLERANCE_SECONDS` (0.05 s). This makes
the non-negotiable "content & timing preserved" requirement a checked invariant.

## Streaming (M5)

`convert_stream` consumes float32 mono chunks and applies an equal-power
overlap-add crossfade (`StreamingConverter`) to hide chunk seams. The model
stays resident (`load_voice` caches per `voice_id`). The M1 window converter
uses a temp-file round-trip for correctness; M5 swaps in in-GPU-memory array
inference to hit the ≤300 ms latency budget.

## Backends

Add a backend by implementing `VoiceConversionBackend` and registering it in
`backends/__init__.py::get_backend`. Nothing else in the engine references a
concrete backend.
