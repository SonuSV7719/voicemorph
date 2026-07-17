# voicemorph-media

ffmpeg/ffprobe wrapper for VoiceMorph. Detects audio-vs-video, extracts audio to
a canonical WAV, and remuxes converted audio back into the original container
with the **video stream copied bit-identically** and subtitles/metadata
preserved. No heavy dependencies.

## Requirements

`ffmpeg` and `ffprobe` on PATH.

## CLI

```bash
voicemorph-media check
voicemorph-media probe input.mp4
voicemorph-media extract input.mp4 audio.wav
voicemorph-media remux input.mp4 converted.wav output.mp4
```
