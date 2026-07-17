import { useState } from "react";
import type { ServerConfig, VoiceMorphClient } from "../api/client";
import { VoiceMorphClient as Client } from "../api/client";

interface Props {
  config: ServerConfig;
  onSave: (c: ServerConfig) => void;
  client: VoiceMorphClient;
}

export function ServerConfigView({ config, onSave }: Props) {
  const [baseUrl, setBaseUrl] = useState(config.baseUrl);
  const [apiKey, setApiKey] = useState(config.apiKey);
  const [test, setTest] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function testConnection() {
    setBusy(true);
    setTest(null);
    try {
      const c = new Client({ baseUrl, apiKey });
      const h = await c.health();
      setTest(`✓ Connected · engine=${h.engine_backend} · jobs=${h.job_mode}`);
    } catch (e) {
      setTest(`✗ ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="view">
      <h2>Server</h2>
      <p className="hint">
        Point the app at your VoiceMorph backend — a local bundled server, a LAN
        machine, or a cloud endpoint.
      </p>

      <label>
        Backend URL
        <input
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder="http://127.0.0.1:8000"
        />
      </label>

      <label>
        API key
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="your API key"
        />
      </label>

      <div className="row">
        <button onClick={testConnection} disabled={busy || !baseUrl}>
          {busy ? "Testing…" : "Test connection"}
        </button>
        <button className="primary" onClick={() => onSave({ baseUrl, apiKey })}>
          Save
        </button>
      </div>

      {test && <div className={test.startsWith("✓") ? "ok" : "err"}>{test}</div>}
    </div>
  );
}
