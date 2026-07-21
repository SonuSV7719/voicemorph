"""Zero-shot CPU voice conversion via Microsoft SpeechT5-VC.

Runs on CPU (and on Python 3.13 — it uses HuggingFace ``transformers``, no
fairseq). There is **no per-voice training**: a target x-vector speaker
embedding is derived once from the reference audio, and any source speech is
converted toward it.

Honest limitations (documented, not hidden):

* SpeechT5-VC outputs **16 kHz** audio and re-synthesizes the waveform, so it
  preserves *content* well but does **not** guarantee frame-exact prosody/timing
  like RVC does. To keep video A/V in sync, the converted audio is fitted to the
  source duration (pad/trim) before it is returned.
* It is a solid "works on CPU today" option; for best fidelity use the Seed-VC
  or RVC backends.

All heavy imports are lazy so importing this module never requires the
``[speecht5]`` extra to be installed.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from pathlib import Path

import numpy as np
import soundfile as sf

# HF's "xet" CDN transfer can be flaky on some networks (CAS client errors);
# fall back to the classic, more reliable download path for model weights.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from voicemorph_engine.backends.base import (
    ConversionParams,
    ConversionResult,
    ProgressCallback,
    StreamConfig,
    TrainingParams,
    TrainingResult,
    VoiceConversionBackend,
)
from voicemorph_engine.config import EngineConfig
from voicemorph_engine.errors import BackendUnavailableError, ProfileNotTrainedError

_SR = 16_000              # SpeechT5 operates at 16 kHz
_CHUNK_SECONDS = 10.0     # process the source in windows to bound memory/quality
_XVECT_SOURCE = "microsoft/wavlm-base-plus-sv"   # transformers-native 512-d speaker embedding


class SpeechT5Backend(VoiceConversionBackend):
    backend_id = "speecht5"

    def __init__(self, config: EngineConfig):
        self.config = config
        self._resident: dict[str, np.ndarray] = {}   # voice_id -> speaker embedding
        self._models = None                          # (processor, model, vocoder)
        self._xvector = None                         # speechbrain classifier

    # -- availability -------------------------------------------------------

    def is_available(self) -> bool:
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
        except Exception:
            return False
        return True

    def _require(self):
        if not self.is_available():
            raise BackendUnavailableError(
                "SpeechT5 backend unavailable. Install the extra: "
                'pip install "voicemorph-engine[speecht5]". Runs on CPU / Python 3.13.'
            )

    # -- lazy model loading -------------------------------------------------

    def _load_models(self):
        if self._models is not None:
            return self._models
        self._require()
        import torch
        from transformers import (
            SpeechT5ForSpeechToSpeech,
            SpeechT5HifiGan,
            SpeechT5Processor,
        )

        cache = str(self.config.models_dir / "speecht5")
        processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_vc", cache_dir=cache)
        model = SpeechT5ForSpeechToSpeech.from_pretrained("microsoft/speecht5_vc", cache_dir=cache)
        vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan", cache_dir=cache)
        model.eval()
        vocoder.eval()
        torch.set_num_threads(max(1, (torch.get_num_threads() or 4)))
        self._models = (processor, model, vocoder)
        return self._models

    def _load_speaker_encoder(self):
        if self._xvector is not None:
            return self._xvector
        self._require()
        # transformers-native 512-d speaker embedding (WavLM-SV). Avoids
        # speechbrain (whose 1.0 lazy-integration scan pulls k2/torchcodec that
        # have no Windows wheels). 512-d matches SpeechT5's speaker_embeddings.
        from transformers import AutoFeatureExtractor, WavLMForXVector

        cache = str(self.config.models_dir / "wavlm_sv")
        fe = AutoFeatureExtractor.from_pretrained(_XVECT_SOURCE, cache_dir=cache)
        model = WavLMForXVector.from_pretrained(_XVECT_SOURCE, cache_dir=cache)
        model.eval()
        self._xvector = (fe, model)
        return self._xvector

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _read_mono_16k(path: Path) -> np.ndarray:
        # Read via soundfile (handles WAV/FLAC/OGG) to avoid torchaudio's
        # torchcodec dependency; resample with a pure-tensor op. Inputs in our
        # pipeline are always WAV extracted by ffmpeg.
        data, sr = sf.read(str(path), dtype="float32", always_2d=False)
        data = np.asarray(data, dtype="float32")
        if data.ndim == 2:
            data = data.mean(axis=1)
        if sr != _SR:
            import torch
            import torchaudio

            data = (
                torchaudio.functional.resample(torch.from_numpy(data), sr, _SR)
                .contiguous()
                .numpy()
                .astype("float32")
            )
        return data

    def _embed_target(self, audio_16k: np.ndarray) -> np.ndarray:
        import torch
        import torch.nn.functional as F

        fe, model = self._load_speaker_encoder()
        with torch.no_grad():
            inputs = fe(audio_16k, sampling_rate=_SR, return_tensors="pt")
            emb = model(**inputs).embeddings  # (1, 512)
            emb = F.normalize(emb, dim=-1).squeeze(0)
        return emb.cpu().numpy().astype("float32")  # (512,)

    # -- "training" = derive + store the target speaker embedding -----------

    def train(
        self,
        voice_id: str,
        dataset_dir: Path,
        output_dir: Path,
        params: TrainingParams,
        progress: ProgressCallback | None = None,
    ) -> TrainingResult:
        self._require()
        output_dir.mkdir(parents=True, exist_ok=True)
        if progress:
            progress(0.1, "reading reference audio")

        # Average x-vectors over all reference clips for a stable target voice.
        clips = sorted(
            p for p in dataset_dir.rglob("*")
            if p.suffix.lower() in {".wav", ".flac", ".mp3", ".ogg", ".m4a"}
        )
        if not clips:
            raise BackendUnavailableError(f"No reference audio found in {dataset_dir}.")

        embs = []
        for i, clip in enumerate(clips):
            audio = self._read_mono_16k(clip)
            if audio.size < _SR // 2:  # skip <0.5s fragments
                continue
            embs.append(self._embed_target(audio))
            if progress:
                progress(0.1 + 0.8 * (i + 1) / len(clips), f"embedding {i + 1}/{len(clips)}")
        if not embs:
            raise BackendUnavailableError("Reference clips too short to embed.")

        speaker = np.mean(np.stack(embs), axis=0).astype("float32")
        model_path = output_dir / "speaker_xvector.npy"
        np.save(model_path, speaker)
        if progress:
            progress(1.0, "target voice embedded")

        return TrainingResult(
            voice_id=voice_id,
            model_path=str(model_path),
            index_path=None,
            epochs_trained=0,
            sample_rate=_SR,
            metrics={"backend": "speecht5", "clips": len(embs), "note": "zero-shot; no training"},
        )

    # -- inference ----------------------------------------------------------

    def load_voice(self, voice_id: str, model_path: Path, index_path: Path | None) -> None:
        self._require()
        self._load_models()
        self._resident[voice_id] = np.load(str(model_path)).astype("float32")

    def convert_file(
        self,
        voice_id: str,
        source_audio: Path,
        output_path: Path,
        params: ConversionParams,
    ) -> ConversionResult:
        self._require()
        if voice_id not in self._resident:
            raise ProfileNotTrainedError(f"Voice {voice_id!r} not loaded. Call load_voice().")
        import time

        import torch

        processor, model, vocoder = self._load_models()
        speaker = torch.tensor(self._resident[voice_id]).unsqueeze(0)  # (1,512)

        source = self._read_mono_16k(source_audio)
        source_duration = source.size / _SR
        output_path.parent.mkdir(parents=True, exist_ok=True)

        t0 = time.perf_counter()
        chunk = int(_CHUNK_SECONDS * _SR)
        pieces: list[np.ndarray] = []
        with torch.no_grad():
            for start in range(0, source.size, chunk):
                seg = source[start : start + chunk]
                if seg.size < _SR // 10:  # skip <0.1s tail
                    continue
                inputs = processor(audio=seg, sampling_rate=_SR, return_tensors="pt")
                speech = model.generate_speech(
                    inputs["input_values"], speaker, vocoder=vocoder
                )
                pieces.append(speech.cpu().numpy().astype("float32"))
        elapsed = time.perf_counter() - t0

        converted = np.concatenate(pieces) if pieces else np.zeros(0, dtype="float32")
        converted = _fit_length(converted, int(round(source_duration * _SR)))
        sf.write(str(output_path), converted, _SR)

        out_duration = converted.size / _SR
        return ConversionResult(
            voice_id=voice_id,
            output_path=str(output_path),
            sample_rate=_SR,
            source_duration=source_duration,
            output_duration=out_duration,
            real_time_factor=(elapsed / source_duration) if source_duration else None,
        )

    def convert_stream(
        self,
        voice_id: str,
        chunks: Iterable[np.ndarray],
        params: ConversionParams,
        stream_config: StreamConfig,
    ) -> Iterator[np.ndarray]:
        # SpeechT5-VC is a seq2seq model — too heavy for low-latency streaming.
        # Real-time streaming is provided by the RVC/Seed-VC backends.
        raise BackendUnavailableError(
            "SpeechT5 backend does not support real-time streaming; use batch conversion "
            "or the rvc/seedvc backend for live mode."
        )

    def unload_voice(self, voice_id: str) -> None:
        self._resident.pop(voice_id, None)


def _fit_length(audio: np.ndarray, target: int) -> np.ndarray:
    """Pad with silence or trim so audio matches the source length (keeps A/V sync)."""
    if target <= 0:
        return audio
    if audio.size < target:
        return np.concatenate([audio, np.zeros(target - audio.size, dtype="float32")])
    return audio[:target]
