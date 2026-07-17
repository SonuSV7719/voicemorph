import { useMemo, useState } from "react";
import { VoiceMorphClient } from "./api/client";
import { useConfig } from "./config";
import { BatchConvert } from "./views/BatchConvert";
import { ServerConfigView } from "./views/ServerConfig";
import { VoiceLibrary } from "./views/VoiceLibrary";

type Tab = "convert" | "voices" | "server";

export function App() {
  const [config, setConfig] = useConfig();
  const [tab, setTab] = useState<Tab>(config.apiKey ? "convert" : "server");

  const client = useMemo(() => new VoiceMorphClient(config), [config]);
  const configured = Boolean(config.baseUrl && config.apiKey);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">🎙️</span> VoiceMorph
        </div>
        <nav className="tabs">
          <button
            className={tab === "convert" ? "active" : ""}
            onClick={() => setTab("convert")}
            disabled={!configured}
          >
            Convert
          </button>
          <button
            className={tab === "voices" ? "active" : ""}
            onClick={() => setTab("voices")}
            disabled={!configured}
          >
            Voices
          </button>
          <button className={tab === "server" ? "active" : ""} onClick={() => setTab("server")}>
            Server
          </button>
        </nav>
      </header>

      <main className="content">
        {!configured && tab !== "server" ? (
          <div className="empty">Configure a server first.</div>
        ) : tab === "convert" ? (
          <BatchConvert client={client} />
        ) : tab === "voices" ? (
          <VoiceLibrary client={client} />
        ) : (
          <ServerConfigView config={config} onSave={setConfig} client={client} />
        )}
      </main>

      <footer className="statusbar">
        <span>{config.baseUrl || "no server"}</span>
        <span className="ethics">Consent required · your voice or documented consent only</span>
      </footer>
    </div>
  );
}
