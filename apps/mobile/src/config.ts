import AsyncStorage from "@react-native-async-storage/async-storage";
import { useCallback, useEffect, useState } from "react";
import type { ServerConfig } from "./api/client";

const KEY = "voicemorph.serverConfig";

const DEFAULT: ServerConfig = { baseUrl: "http://10.0.2.2:8000", apiKey: "" };

export function useConfig(): {
  config: ServerConfig;
  setConfig: (c: ServerConfig) => void;
  loaded: boolean;
} {
  const [config, setConfigState] = useState<ServerConfig>(DEFAULT);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((raw) => {
        if (raw) setConfigState({ ...DEFAULT, ...(JSON.parse(raw) as Partial<ServerConfig>) });
      })
      .catch(() => undefined)
      .finally(() => setLoaded(true));
  }, []);

  const setConfig = useCallback((c: ServerConfig) => {
    setConfigState(c);
    void AsyncStorage.setItem(KEY, JSON.stringify(c));
  }, []);

  return { config, setConfig, loaded };
}

const VOICES_KEY = "voicemorph.voiceIds";

export async function loadVoiceIds(): Promise<string[]> {
  try {
    const raw = await AsyncStorage.getItem(VOICES_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

export async function saveVoiceIds(ids: string[]): Promise<void> {
  await AsyncStorage.setItem(VOICES_KEY, JSON.stringify(ids));
}
