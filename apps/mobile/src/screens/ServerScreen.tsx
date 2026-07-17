import { useState } from "react";
import { ScrollView, Text, TextInput, TouchableOpacity, View } from "react-native";
import { type ServerConfig, VoiceMorphClient } from "../api/client";
import { styles } from "../theme";

interface Props {
  config: ServerConfig;
  onSave: (c: ServerConfig) => void;
}

export function ServerScreen({ config, onSave }: Props) {
  const [baseUrl, setBaseUrl] = useState(config.baseUrl);
  const [apiKey, setApiKey] = useState(config.apiKey);
  const [test, setTest] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function testConnection() {
    setBusy(true);
    setTest(null);
    try {
      const h = await new VoiceMorphClient({ baseUrl, apiKey }).health();
      setTest(`✓ Connected · engine=${h.engine_backend} · jobs=${h.job_mode}`);
    } catch (e) {
      setTest(`✗ ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView style={styles.screen}>
      <Text style={styles.h2}>Server</Text>
      <Text style={styles.hint}>
        Point the app at your VoiceMorph backend. On an Android emulator the host
        machine is 10.0.2.2; on a physical device use your server's LAN IP.
      </Text>

      <Text style={styles.label}>Backend URL</Text>
      <TextInput
        style={styles.input}
        value={baseUrl}
        onChangeText={setBaseUrl}
        autoCapitalize="none"
        autoCorrect={false}
        placeholder="http://10.0.2.2:8000"
        placeholderTextColor="#5a6172"
      />

      <Text style={styles.label}>API key</Text>
      <TextInput
        style={styles.input}
        value={apiKey}
        onChangeText={setApiKey}
        secureTextEntry
        autoCapitalize="none"
        placeholder="your API key"
        placeholderTextColor="#5a6172"
      />

      <View style={styles.row}>
        <TouchableOpacity style={styles.button} onPress={testConnection} disabled={busy}>
          <Text style={styles.buttonText}>{busy ? "Testing…" : "Test connection"}</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.button, styles.buttonPrimary]}
          onPress={() => onSave({ baseUrl, apiKey })}
        >
          <Text style={[styles.buttonText, styles.buttonTextPrimary]}>Save</Text>
        </TouchableOpacity>
      </View>

      {test && <Text style={test.startsWith("✓") ? styles.ok : styles.err}>{test}</Text>}
    </ScrollView>
  );
}
