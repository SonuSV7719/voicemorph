// Persisted server configuration (localStorage) + a small React hook.
import { useCallback, useEffect, useState } from "react";
import type { ServerConfig } from "./api/client";

const KEY = "voicemorph.serverConfig";

const DEFAULT: ServerConfig = {
  baseUrl: "http://127.0.0.1:8000",
  apiKey: "",
};

export function loadConfig(): ServerConfig {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return { ...DEFAULT, ...(JSON.parse(raw) as Partial<ServerConfig>) };
  } catch {
    /* ignore corrupt storage */
  }
  return DEFAULT;
}

export function useConfig(): [ServerConfig, (c: ServerConfig) => void] {
  const [config, setConfigState] = useState<ServerConfig>(loadConfig);

  const setConfig = useCallback((c: ServerConfig) => {
    setConfigState(c);
    localStorage.setItem(KEY, JSON.stringify(c));
  }, []);

  useEffect(() => {
    localStorage.setItem(KEY, JSON.stringify(config));
  }, [config]);

  return [config, setConfig];
}
