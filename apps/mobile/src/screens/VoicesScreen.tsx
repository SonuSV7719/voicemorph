import * as DocumentPicker from "expo-document-picker";
import { useCallback, useEffect, useState } from "react";
import { ScrollView, Switch, Text, TextInput, TouchableOpacity, View } from "react-native";
import type { FilePart, VoiceMorphClient, VoiceStatus } from "../api/client";
import { loadVoiceIds, saveVoiceIds } from "../config";
import { colors, styles } from "../theme";

interface Props {
  client: VoiceMorphClient;
}

export function VoicesScreen({ client }: Props) {
  const [voiceIds, setVoiceIds] = useState<string[]>([]);
  const [statuses, setStatuses] = useState<Record<string, VoiceStatus>>({});

  const [name, setName] = useState("");
  const [subject, setSubject] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [files, setFiles] = useState<FilePart[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadVoiceIds().then(setVoiceIds);
  }, []);

  const refresh = useCallback(async () => {
    const next: Record<string, VoiceStatus> = {};
    await Promise.all(
      voiceIds.map(async (id) => {
        try {
          next[id] = await client.voiceStatus(id);
        } catch {
          /* skip */
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

  async function pickSamples() {
    const res = await DocumentPicker.getDocumentAsync({ type: "audio/*", multiple: true });
    if (res.canceled) return;
    setFiles(
      res.assets.map((a) => ({ uri: a.uri, name: a.name, mimeType: a.mimeType })),
    );
  }

  async function createVoice() {
    setError(null);
    if (!confirmed) return setError("You must confirm you have the right to use this voice.");
    if (files.length === 0) return setError("Add at least one voice sample.");
    setBusy(true);
    try {
      const created = await client.createVoice(
        name || subject,
        { subject, granted_by: subject, method: "self", confirmed },
        files,
      );
      const ids = [created.voice_id, ...voiceIds];
      setVoiceIds(ids);
      await saveVoiceIds(ids);
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

  return (
    <ScrollView style={styles.screen}>
      <Text style={styles.h2}>Voice profiles</Text>

      <View style={styles.card}>
        <Text style={styles.h3}>New profile</Text>
        <Text style={styles.ethics}>
          Only from your own voice or a voice you have documented consent to use.
        </Text>

        <Text style={styles.label}>Display name</Text>
        <TextInput style={styles.input} value={name} onChangeText={setName} placeholder="My Voice" placeholderTextColor="#5a6172" />

        <Text style={styles.label}>Subject (whose voice)</Text>
        <TextInput style={styles.input} value={subject} onChangeText={setSubject} placeholder="Name" placeholderTextColor="#5a6172" />

        <TouchableOpacity style={styles.button} onPress={pickSamples}>
          <Text style={styles.buttonText}>
            {files.length ? `${files.length} sample(s) selected` : "Pick voice samples"}
          </Text>
        </TouchableOpacity>

        <View style={[styles.row, { marginTop: 12 }]}>
          <Switch value={confirmed} onValueChange={setConfirmed} />
          <Text style={[styles.hint, { flex: 1, color: colors.text }]}>
            I confirm I have the right to use this voice.
          </Text>
        </View>

        <TouchableOpacity
          style={[styles.button, styles.buttonPrimary]}
          onPress={createVoice}
          disabled={busy}
        >
          <Text style={[styles.buttonText, styles.buttonTextPrimary]}>
            {busy ? "Creating…" : "Create & train"}
          </Text>
        </TouchableOpacity>
        {error && <Text style={styles.err}>{error}</Text>}
      </View>

      <View style={styles.card}>
        <Text style={styles.h3}>Library</Text>
        {voiceIds.length === 0 ? (
          <Text style={styles.empty}>No profiles yet.</Text>
        ) : (
          voiceIds.map((id) => {
            const s = statuses[id];
            return (
              <View
                key={id}
                style={{
                  flexDirection: "row",
                  justifyContent: "space-between",
                  paddingVertical: 8,
                  borderBottomColor: colors.border,
                  borderBottomWidth: 1,
                }}
              >
                <Text style={{ color: colors.text }}>{s?.name ?? id.slice(0, 8)}</Text>
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>{s?.ready ? "ready ✓" : (s?.status ?? "…")}</Text>
                </View>
              </View>
            );
          })
        )}
      </View>
    </ScrollView>
  );
}
