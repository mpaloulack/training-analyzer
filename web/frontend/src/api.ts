export interface RunParams {
  athlete_id: string;
  api_key: string;
  start: string;
  end: string;
  fcm: number;
  lthr: number;
  fetch_intervals: boolean;
}

export interface RunCallbacks {
  onProgress: (message: string) => void;
}

interface DoneEvent {
  type: "done";
  filename: string;
  zip_b64: string;
}
interface ProgressEvent {
  type: "progress";
  message: string;
}
interface ErrorEvent {
  type: "error";
  message: string;
}
type RunEvent = DoneEvent | ProgressEvent | ErrorEvent;

function b64ToBlob(b64: string): Blob {
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  return new Blob([bytes], { type: "application/zip" });
}

/**
 * POST the params and consume the NDJSON progress stream. Progress lines are
 * delivered via `onProgress`; resolves with the result zip Blob and filename.
 */
export async function runAnalysis(
  params: RunParams,
  { onProgress }: RunCallbacks,
): Promise<{ blob: Blob; filename: string }> {
  const res = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });

  if (!res.ok || !res.body) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON / streamed error */
    }
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: { blob: Blob; filename: string } | null = null;

  for (;;) {
    const { done, value } = await reader.read();
    if (value) buffer += decoder.decode(value, { stream: true });

    let nl: number;
    while ((nl = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, nl).trim();
      buffer = buffer.slice(nl + 1);
      if (!line) continue;
      const event = JSON.parse(line) as RunEvent;
      if (event.type === "progress") onProgress(event.message);
      else if (event.type === "error") throw new Error(event.message);
      else if (event.type === "done") result = { blob: b64ToBlob(event.zip_b64), filename: event.filename };
    }
    if (done) break;
  }

  if (!result) throw new Error("Stream ended without a result.");
  return result;
}

/** Trigger a browser download of a blob without persisting anything server-side. */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
