import { useCallback, useEffect, useState } from "react";
import type { VoiceMorphClient, VoiceStatus } from "../api/client";

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

function saveVoiceIds(ids: string[]) {
  localStorage.setItem(STORE_KEY, JSON.stringify(ids));
}

export function VoiceLibrary({ client }: Props) {
  const [voiceIds, setVoiceIds] = useState<string[]>(loadVoiceIds);
  const [statuses, setStatuses] = useState<Record<string, VoiceStatus>>({});

  // Create-voice form.
  const [name, setName] = useState("");
  const [subject, setSubject] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const next: Record<string, VoiceStatus> = {};
    await Promise.all(
      voiceIds.map(async (id) => {
        try {
          next[id] = await client.voiceStatus(id);
        } catch {
          /* skip unreachable/missing */
        }
      }),
    );
    setStatuses(next);
  }, [client, voiceIds]);

  useEffect(() => {
    void refresh();
    const t = setInterval(refresh, 3000);
    return () => clearInterval(t);
  }, [refresh]);

  async function createVoice() {
    setError(null);
    if (!confirmed) {
      setError("You must confirm you have the right to use this voice.");
      return;
    }
    if (files.length === 0) {
      setError("Add at least one voice sample.");
      return;
    }
    setBusy(true);
    try {
      const created = await client.createVoice(
        name || subject,
        { subject, granted_by: subject, method: "self", confirmed },
        files,
      );
      const ids = [created.voice_id, ...voiceIds];
      setVoiceIds(ids);
      saveVoiceIds(ids);
      setName("");
      setSubject("");
      setConfirmed(false);
      setFiles([]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function forget(id: string) {
    const ids = voiceIds.filter((v) => v !== id);
    setVoiceIds(ids);
    saveVoiceIds(ids);
  }

  return (
    <div className="view">
      <h2>Voice profiles</h2>

      <section className="card">
        <h3>New profile</h3>
        <p className="hint ethics">
          Only create a profile from your own voice or a voice you have explicit,
          documented consent to use.
        </p>
        <label>
          Display name
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. My Voice" />
        </label>
        <label>
          Subject (whose voice)
          <input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Name" />
        </label>
        <label>
          Voice samples (10–30 min of clean audio recommended)
          <input
            type="file"
            accept="audio/*"
            multiple
            onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
          />
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          I confirm I have the right to use this voice (my own, or with consent).
        </label>
        <button className="primary" onClick={createVoice} disabled={busy}>
          {busy ? "Creating…" : "Create & train"}
        </button>
        {error && <div className="err">{error}</div>}
      </section>

      <section className="card">
        <h3>Library</h3>
        {voiceIds.length === 0 ? (
          <div className="empty">No profiles yet.</div>
        ) : (
          <table className="grid">
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Ready</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {voiceIds.map((id) => {
                const s = statuses[id];
                return (
                  <tr key={id}>
                    <td>{s?.name ?? id.slice(0, 8)}</td>
                    <td>
                      <span className={`badge ${s?.status ?? "unknown"}`}>
                        {s?.status ?? "…"}
                      </span>
                      {s?.error && <div className="err small">{s.error}</div>}
                    </td>
                    <td>{s?.ready ? "✓" : ""}</td>
                    <td>
                      <button className="link" onClick={() => forget(id)}>
                        Forget
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
