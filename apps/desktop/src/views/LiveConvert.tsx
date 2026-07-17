import { useCallback, useEffect, useRef, useState } from "react";
import type { ServerConfig, VoiceMorphClient, VoiceStatus } from "../api/client";
import { LiveSession, type LiveStatus } from "../live/stream";

interface Props {
  client: VoiceMorphClient;
  config: ServerConfig;
}

const STORE_KEY = "voicemorph.voiceIds";

function loadVoiceIds(): string[] {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY) ?? "[]") as string[];
  } catch {
    return [];
  }
}

export function LiveConvert({ client, config }: Props) {
  const [voices, setVoices] = useState<VoiceStatus[]>([]);
  const [voiceId, setVoiceId] = useState("");
  const [status, setStatus] = useState<LiveStatus>("idle");
  const [detail, setDetail] = useState<string | null>(null);
  const sessionRef = useRef<LiveSession | null>(null);

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
    return () => {
      void sessionRef.current?.stop();
    };
  }, [loadReadyVoices]);

  async function start() {
    if (!voiceId) return;
    setDetail(null);
    const session = new LiveSession(config, voiceId, (s, d) => {
      setStatus(s);
      if (d) setDetail(d);
    });
    sessionRef.current = session;
    try {
      await session.start();
    } catch {
      /* status already surfaced via callback */
    }
  }

  async function stop() {
    await sessionRef.current?.stop();
    sessionRef.current = null;
  }

  const live = status === "live" || status === "connecting";

  return (
    <div className="view">
      <h2>Live mode</h2>
      <p className="hint">
        Convert your microphone in real time. Latency depends on the model and
        network; expect ~200–300 ms on a consumer GPU plus network time.
      </p>

      {voices.length === 0 ? (
        <div className="empty">
          No trained voices yet. Create one under <strong>Voices</strong> first.
        </div>
      ) : (
        <>
          <label>
            Target voice
            <select
              value={voiceId}
              onChange={(e) => setVoiceId(e.target.value)}
              disabled={live}
            >
              {voices.map((v) => (
                <option key={v.voice_id} value={v.voice_id}>
                  {v.name}
                </option>
              ))}
            </select>
          </label>

          <div className="row">
            {!live ? (
              <button className="primary" onClick={start} disabled={!voiceId}>
                Start mic
              </button>
            ) : (
              <button onClick={stop}>Stop</button>
            )}
            <span className={`badge ${status === "live" ? "ready" : ""}`}>
              {status === "live" ? "● live" : status}
            </span>
          </div>

          <p className="hint ethics">
            Streamed audio is converted on your configured server. Use only voices
            you own or have consent to use.
          </p>
          {detail && <div className={status === "error" ? "err" : "hint"}>{detail}</div>}
        </>
      )}
    </div>
  );
}
