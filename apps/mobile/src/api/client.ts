// Typed VoiceMorph backend client for React Native.
// Uploads use RN FormData file parts ({ uri, name, type }) rather than browser File.

export interface ServerConfig {
  baseUrl: string;
  apiKey: string;
}

export interface FilePart {
  uri: string;
  name: string;
  mimeType?: string;
}

export interface VoiceCreated {
  voice_id: string;
  name: string;
  status: string;
}

export interface VoiceStatus {
  voice_id: string;
  name: string;
  status: string;
  ready: boolean;
  error?: string | null;
  dataset_seconds?: number | null;
}

export type JobState = "queued" | "running" | "succeeded" | "failed";

export interface Job {
  job_id: string;
  kind: "train" | "convert";
  state: JobState;
  progress: number;
  message?: string | null;
  voice_id?: string | null;
  result_key?: string | null;
  output_kind?: "audio" | "video" | null;
  error?: string | null;
}

export interface Consent {
  subject: string;
  granted_by?: string;
  method?: string;
  reference?: string;
  confirmed: boolean;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function rnFilePart(f: FilePart) {
  // React Native's fetch understands this shape for multipart file fields.
  return { uri: f.uri, name: f.name, type: f.mimeType ?? "application/octet-stream" } as unknown as Blob;
}

export class VoiceMorphClient {
  constructor(private config: ServerConfig) {}

  private headers(extra?: Record<string, string>): Record<string, string> {
    return { "X-API-Key": this.config.apiKey, ...(extra ?? {}) };
  }

  private url(path: string): string {
    return `${this.config.baseUrl.replace(/\/$/, "")}${path}`;
  }

  private async parse<T>(res: Response): Promise<T> {
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = (await res.json()) as { detail?: string };
        detail = body.detail ?? detail;
      } catch {
        /* non-JSON error body */
      }
      throw new ApiError(res.status, detail);
    }
    return (await res.json()) as T;
  }

  async health(): Promise<{ status: string; engine_backend: string; job_mode: string }> {
    return this.parse(await fetch(this.url("/health")));
  }

  async createVoice(
    name: string,
    consent: Consent,
    files: FilePart[],
    epochs = 200,
  ): Promise<VoiceCreated> {
    const form = new FormData();
    form.append("name", name);
    form.append("consent", JSON.stringify(consent));
    form.append("epochs", String(epochs));
    for (const f of files) form.append("files", rnFilePart(f));
    return this.parse(
      await fetch(this.url("/voices"), { method: "POST", headers: this.headers(), body: form }),
    );
  }

  async voiceStatus(voiceId: string): Promise<VoiceStatus> {
    return this.parse(
      await fetch(this.url(`/voices/${voiceId}/status`), { headers: this.headers() }),
    );
  }

  async convertBatch(
    voiceId: string,
    file: FilePart,
    params: { transpose?: number; index_rate?: number; protect?: number } = {},
  ): Promise<Job> {
    const form = new FormData();
    form.append("voice_id", voiceId);
    form.append("transpose", String(params.transpose ?? 0));
    form.append("index_rate", String(params.index_rate ?? 0.75));
    form.append("protect", String(params.protect ?? 0.33));
    form.append("file", rnFilePart(file));
    return this.parse(
      await fetch(this.url("/convert/batch"), { method: "POST", headers: this.headers(), body: form }),
    );
  }

  async jobStatus(jobId: string): Promise<Job> {
    return this.parse(
      await fetch(this.url(`/convert/batch/${jobId}`), { headers: this.headers() }),
    );
  }

  downloadUrl(jobId: string): string {
    return this.url(`/convert/batch/${jobId}/download`);
  }

  async pollJob(jobId: string, onUpdate: (j: Job) => void, intervalMs = 1500): Promise<Job> {
    for (;;) {
      const job = await this.jobStatus(jobId);
      onUpdate(job);
      if (job.state === "succeeded" || job.state === "failed") return job;
      await new Promise((r) => setTimeout(r, intervalMs));
    }
  }
}
