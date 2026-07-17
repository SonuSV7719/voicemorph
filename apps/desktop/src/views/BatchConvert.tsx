import { useCallback, useEffect, useState } from "react";
import type { Job, VoiceMorphClient, VoiceStatus } from "../api/client";

interface Props {
  client: VoiceMorphClient;
}

const STORE_KEY = "voicemorph.voiceIds";

function loadVoiceIds(): string[] {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY) ?? "[]") as string[];
  } catch {
    return [];
  }
}

export function BatchConvert({ client }: Props) {
  const [voices, setVoices] = useState<VoiceStatus[]>([]);
  const [voiceId, setVoiceId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadReadyVoices = useCallback(async () => {
    const ids = loadVoiceIds();
    const out: VoiceStatus[] = [];
    await Promise.all(
      ids.map(async (id) => {
        try {
          const s = await client.voiceStatus(id);
          if (s.ready) out.push(s);
        } catch {
          /* skip */
        }
      }),
    );
    setVoices(out);
    if (out.length && !out.find((v) => v.voice_id === voiceId)) setVoiceId(out[0].voice_id);
  }, [client, voiceId]);

  useEffect(() => {
    void loadReadyVoices();
  }, [loadReadyVoices]);

  async function convert() {
    if (!voiceId || !file) return;
    setError(null);
    setBusy(true);
    setJob(null);
    try {
      const started = await client.convertBatch(voiceId, file);
      setJob(started);
      const final = await client.pollJob(started.job_id, setJob);
      if (final.state === "failed") setError(final.error ?? "Conversion failed.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function download() {
    if (!job || job.state !== "succeeded") return;
    const blob = await client.downloadResult(job.job_id);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const ext = job.output_kind === "video" ? "mp4" : "wav";
    a.download = `voicemorph_${job.job_id.slice(0, 8)}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="view">
      <h2>Batch convert</h2>

      {voices.length === 0 ? (
        <div className="empty">
          No trained voices yet. Create one under <strong>Voices</strong> first.
        </div>
      ) : (
        <>
          <label>
            Target voice
            <select value={voiceId} onChange={(e) => setVoiceId(e.target.value)}>
              {voices.map((v) => (
                <option key={v.voice_id} value={v.voice_id}>
                  {v.name}
                </option>
              ))}
            </select>
          </label>

          <div
            className={`dropzone ${dragOver ? "over" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const f = e.dataTransfer.files?.[0];
              if (f) setFile(f);
            }}
          >
            {file ? (
              <div>
                <strong>{file.name}</strong>
                <div className="hint">{(file.size / 1_000_000).toFixed(1)} MB</div>
              </div>
            ) : (
              <div className="hint">Drag an audio or video file here, or</div>
            )}
            <input
              type="file"
              accept="audio/*,video/*"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>

          <button className="primary" onClick={convert} disabled={busy || !file}>
            {busy ? "Converting…" : "Convert"}
          </button>

          {job && (
            <div className="job">
              <div className="progress">
                <div className="bar" style={{ width: `${Math.round(job.progress * 100)}%` }} />
              </div>
              <div className="hint">
                {job.state} · {job.message ?? ""}
              </div>
              {job.state === "succeeded" && (
                <button className="primary" onClick={download}>
                  Download {job.output_kind === "video" ? "video" : "audio"}
                </button>
              )}
            </div>
          )}

          {error && <div className="err">{error}</div>}
        </>
      )}
    </div>
  );
}
