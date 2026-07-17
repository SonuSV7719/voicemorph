// Live real-time conversion: mic → WebSocket → speaker.
//
// Capture and playback run in AudioWorklets (audio render thread). PCM frames
// are little-endian float32 mono at the negotiated sample rate — the same wire
// format the backend WS and examples/stream_client.py use.

import type { ServerConfig } from "../api/client";

const SAMPLE_RATE = 40_000;
const FRAME_SIZE = 4800; // ~0.12 s at 40 kHz

export type LiveStatus = "idle" | "connecting" | "live" | "stopped" | "error";

function toWsUrl(baseUrl: string, voiceId: string, apiKey: string): string {
  const base = baseUrl.replace(/^http/, "ws").replace(/\/$/, "");
  return `${base}/convert/stream/${voiceId}?api_key=${encodeURIComponent(apiKey)}`;
}

export class LiveSession {
  private ctx: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private ws: WebSocket | null = null;
  private capture: AudioWorkletNode | null = null;
  private playback: AudioWorkletNode | null = null;

  constructor(
    private config: ServerConfig,
    private voiceId: string,
    private onStatus: (s: LiveStatus, detail?: string) => void,
  ) {}

  async start(): Promise<void> {
    this.onStatus("connecting");
    try {
      this.ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
      await this.ctx.audioWorklet.addModule("/capture-processor.js");
      await this.ctx.audioWorklet.addModule("/playback-processor.js");

      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });

      const source = this.ctx.createMediaStreamSource(this.stream);
      this.capture = new AudioWorkletNode(this.ctx, "capture-processor", {
        processorOptions: { frameSize: FRAME_SIZE },
      });
      this.playback = new AudioWorkletNode(this.ctx, "playback-processor");

      // Keep the capture node in the active graph (muted) so it keeps pulling.
      const mute = this.ctx.createGain();
      mute.gain.value = 0;
      source.connect(this.capture);
      this.capture.connect(mute).connect(this.ctx.destination);
      this.playback.connect(this.ctx.destination);

      await this.connectWs();

      this.capture.port.onmessage = (e: MessageEvent<Float32Array>) => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(e.data.buffer);
        }
      };
    } catch (err) {
      this.onStatus("error", (err as Error).message);
      await this.stop();
      throw err;
    }
  }

  private connectWs(): Promise<void> {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(toWsUrl(this.config.baseUrl, this.voiceId, this.config.apiKey));
      ws.binaryType = "arraybuffer";
      this.ws = ws;
      ws.onopen = () => {
        this.onStatus("live");
        resolve();
      };
      ws.onerror = () => {
        this.onStatus("error", "WebSocket error");
        reject(new Error("WebSocket error"));
      };
      ws.onclose = () => {
        if (this.ctx) this.onStatus("stopped");
      };
      ws.onmessage = (e: MessageEvent<ArrayBuffer>) => {
        if (this.playback) this.playback.port.postMessage(new Float32Array(e.data));
      };
    });
  }

  async stop(): Promise<void> {
    this.ws?.close();
    this.ws = null;
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.capture?.disconnect();
    this.playback?.disconnect();
    this.capture = null;
    this.playback = null;
    if (this.ctx) {
      await this.ctx.close();
      this.ctx = null;
    }
    this.onStatus("stopped");
  }
}
