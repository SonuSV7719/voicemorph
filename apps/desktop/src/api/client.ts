// Typed client for the VoiceMorph backend REST API.
// Mirrors backend/voicemorph_backend/schemas.py.

export interface ServerConfig {
  baseUrl: string;
  apiKey: string;
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
        const body = await res.json();
        detail = (body as { detail?: string }).detail ?? detail;
      } catch {
        /* non-JSON error body */
      }
      throw new ApiError(res.status, detail);
    }
    return (await res.json()) as T;
  }

  async health(): Promise<{ status: string; engine_backend: string; job_mode: string }> {
    const res = await fetch(this.url("/health"));
    return this.parse(res);
  }

  async createVoice(
    name: string,
    consent: Consent,
    files: File[],
    epochs = 200,
  ): Promise<VoiceCreated> {
    const form = new FormData();
    form.append("name", name);
    form.append("consent", JSON.stringify(consent));
    form.append("epochs", String(epochs));
    for (const f of files) form.append("files", f, f.name);
    const res = await fetch(this.url("/voices"), {
      method: "POST",
      headers: this.headers(),
      body: form,
    });
    return this.parse(res);
  }

  async voiceStatus(voiceId: string): Promise<VoiceStatus> {
    const res = await fetch(this.url(`/voices/${voiceId}/status`), {
      headers: this.headers(),
    });
    return this.parse(res);
  }

  async convertBatch(
    voiceId: string,
    file: File,
    params: { transpose?: number; index_rate?: number; protect?: number } = {},
  ): Promise<Job> {
    const form = new FormData();
    form.append("voice_id", voiceId);
    form.append("transpose", String(params.transpose ?? 0));
    form.append("index_rate", String(params.index_rate ?? 0.75));
    form.append("protect", String(params.protect ?? 0.33));
    form.append("file", file, file.name);
    const res = await fetch(this.url("/convert/batch"), {
      method: "POST",
      headers: this.headers(),
      body: form,
    });
    return this.parse(res);
  }

  async jobStatus(jobId: string): Promise<Job> {
    const res = await fetch(this.url(`/convert/batch/${jobId}`), {
      headers: this.headers(),
    });
    return this.parse(res);
  }

  downloadUrl(jobId: string): string {
    return this.url(`/convert/batch/${jobId}/download`);
  }

  async downloadResult(jobId: string): Promise<Blob> {
    const res = await fetch(this.downloadUrl(jobId), { headers: this.headers() });
    if (!res.ok) throw new ApiError(res.status, res.statusText);
    return res.blob();
  }

  /** Poll a job until it reaches a terminal state. */
  async pollJob(
    jobId: string,
    onUpdate: (job: Job) => void,
    intervalMs = 1000,
  ): Promise<Job> {
    for (;;) {
      const job = await this.jobStatus(jobId);
      onUpdate(job);
      if (job.state === "succeeded" || job.state === "failed") return job;
      await new Promise((r) => setTimeout(r, intervalMs));
    }
  }
}
