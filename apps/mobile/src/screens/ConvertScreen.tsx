import * as DocumentPicker from "expo-document-picker";
import * as FileSystem from "expo-file-system";
import { useCallback, useEffect, useState } from "react";
import { ScrollView, Text, TouchableOpacity, View } from "react-native";
import type { FilePart, Job, VoiceMorphClient, VoiceStatus } from "../api/client";
import { loadVoiceIds } from "../config";
import { colors, styles } from "../theme";

interface Props {
  client: VoiceMorphClient;
}

export function ConvertScreen({ client }: Props) {
  const [voices, setVoices] = useState<VoiceStatus[]>([]);
  const [voiceId, setVoiceId] = useState("");
  const [file, setFile] = useState<FilePart | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);

  const loadReady = useCallback(async () => {
    const ids = await loadVoiceIds();
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
    void loadReady();
  }, [loadReady]);

  async function pickSource() {
    const res = await DocumentPicker.getDocumentAsync({ type: ["audio/*", "video/*"] });
    if (res.canceled) return;
    const a = res.assets[0];
    setFile({ uri: a.uri, name: a.name, mimeType: a.mimeType });
  }

  async function convert() {
    if (!voiceId || !file) return;
    setError(null);
    setSaved(null);
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
    const ext = job.output_kind === "video" ? "mp4" : "wav";
    const dest = `${FileSystem.documentDirectory}voicemorph_${job.job_id.slice(0, 8)}.${ext}`;
    const res = await FileSystem.downloadAsync(client.downloadUrl(job.job_id), dest, {
      headers: { "X-API-Key": (client as unknown as { config: { apiKey: string } }).config.apiKey },
    });
    setSaved(res.uri);
  }

  return (
    <ScrollView style={styles.screen}>
      <Text style={styles.h2}>Batch convert</Text>

      {voices.length === 0 ? (
        <Text style={styles.empty}>No trained voices yet. Create one under Voices first.</Text>
      ) : (
        <>
          <Text style={styles.label}>Target voice</Text>
          <View style={styles.card}>
            {voices.map((v) => (
              <TouchableOpacity
                key={v.voice_id}
                style={{ paddingVertical: 8, flexDirection: "row", alignItems: "center", gap: 8 }}
                onPress={() => setVoiceId(v.voice_id)}
              >
                <View
                  style={{
                    width: 16,
                    height: 16,
                    borderRadius: 8,
                    borderWidth: 2,
                    borderColor: voiceId === v.voice_id ? colors.accent : colors.border,
                    backgroundColor: voiceId === v.voice_id ? colors.accent : "transparent",
                  }}
                />
                <Text style={{ color: colors.text }}>{v.name}</Text>
              </TouchableOpacity>
            ))}
          </View>

          <TouchableOpacity style={styles.button} onPress={pickSource}>
            <Text style={styles.buttonText}>{file ? file.name : "Pick audio / video file"}</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.button, styles.buttonPrimary]}
            onPress={convert}
            disabled={busy || !file}
          >
            <Text style={[styles.buttonText, styles.buttonTextPrimary]}>
              {busy ? "Converting…" : "Convert"}
            </Text>
          </TouchableOpacity>

          {job && (
            <View style={{ marginTop: 12 }}>
              <View style={styles.progressTrack}>
                <View style={[styles.progressBar, { width: `${Math.round(job.progress * 100)}%` }]} />
              </View>
              <Text style={styles.hint}>
                {job.state} · {job.message ?? ""}
              </Text>
              {job.state === "succeeded" && (
                <TouchableOpacity style={[styles.button, styles.buttonPrimary]} onPress={download}>
                  <Text style={[styles.buttonText, styles.buttonTextPrimary]}>
                    Download {job.output_kind === "video" ? "video" : "audio"}
                  </Text>
                </TouchableOpacity>
              )}
            </View>
          )}

          {saved && <Text style={styles.ok}>Saved to {saved}</Text>}
          {error && <Text style={styles.err}>{error}</Text>}
        </>
      )}
    </ScrollView>
  );
}
