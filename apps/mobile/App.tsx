import { StatusBar } from "expo-status-bar";
import { useMemo, useState } from "react";
import { SafeAreaView, Text, TouchableOpacity, View } from "react-native";
import { VoiceMorphClient } from "./src/api/client";
import { useConfig } from "./src/config";
import { ConvertScreen } from "./src/screens/ConvertScreen";
import { ServerScreen } from "./src/screens/ServerScreen";
import { VoicesScreen } from "./src/screens/VoicesScreen";
import { colors, styles } from "./src/theme";

type Tab = "convert" | "voices" | "server";

export default function App() {
  const { config, setConfig, loaded } = useConfig();
  const [tab, setTab] = useState<Tab>("convert");
  const client = useMemo(() => new VoiceMorphClient(config), [config]);
  const configured = Boolean(config.baseUrl && config.apiKey);

  const effectiveTab: Tab = !configured && tab !== "server" ? "server" : tab;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }}>
      <StatusBar style="light" />
      <View
        style={{
          paddingHorizontal: 16,
          paddingVertical: 12,
          backgroundColor: colors.panel,
          borderBottomColor: colors.border,
          borderBottomWidth: 1,
        }}
      >
        <Text style={{ color: colors.text, fontWeight: "700", fontSize: 18 }}>🎙️ VoiceMorph</Text>
      </View>

      <View style={{ flex: 1 }}>
        {!loaded ? (
          <Text style={styles.empty}>Loading…</Text>
        ) : effectiveTab === "convert" ? (
          <ConvertScreen client={client} />
        ) : effectiveTab === "voices" ? (
          <VoicesScreen client={client} />
        ) : (
          <ServerScreen config={config} onSave={setConfig} />
        )}
      </View>

      <View style={styles.tabbar}>
        {(["convert", "voices", "server"] as Tab[]).map((t) => {
          const disabled = !configured && t !== "server";
          return (
            <TouchableOpacity
              key={t}
              style={[styles.tab, effectiveTab === t && styles.tabActive]}
              disabled={disabled}
              onPress={() => setTab(t)}
            >
              <Text
                style={[
                  styles.tabText,
                  effectiveTab === t && styles.tabTextActive,
                  disabled && { opacity: 0.4 },
                ]}
              >
                {t[0].toUpperCase() + t.slice(1)}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </SafeAreaView>
  );
}
