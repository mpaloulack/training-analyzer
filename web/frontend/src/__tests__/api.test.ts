import { afterEach, describe, expect, it, vi } from "vitest";
import { runAnalysis, type RunParams } from "../api";

const PARAMS: RunParams = {
  athlete_id: "882231",
  api_key: "abcd1234efgh5678",
  start: "2026-01-01",
  end: "2026-03-01",
  fcm: 196,
  lthr: 181,
  fetch_intervals: true,
};

/** Build a fake streaming Response whose body emits the given NDJSON lines. */
function streamResponse(events: object[], opts: { ok?: boolean; status?: number } = {}) {
  const encoder = new TextEncoder();
  const lines = events.map((e) => JSON.stringify(e) + "\n");
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      // Split across chunks to exercise the line buffering.
      for (const l of lines) {
        controller.enqueue(encoder.encode(l.slice(0, 3)));
        controller.enqueue(encoder.encode(l.slice(3)));
      }
      controller.close();
    },
  });
  return { ok: opts.ok ?? true, status: opts.status ?? 200, body } as unknown as Response;
}

afterEach(() => vi.restoreAllMocks());

describe("runAnalysis", () => {
  it("posts params, reports progress, and returns the zip", async () => {
    const zip_b64 = btoa("zipbytes");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        streamResponse([
          { type: "progress", message: "1/3 Activités…" },
          { type: "progress", message: "🎨 Generating graphs…" },
          { type: "done", filename: "training-analysis.zip", zip_b64 },
        ]),
      ),
    );

    const seen: string[] = [];
    const result = await runAnalysis(PARAMS, { onProgress: (m) => seen.push(m) });

    expect(seen).toEqual(["1/3 Activités…", "🎨 Generating graphs…"]);
    expect(result.filename).toBe("training-analysis.zip");
    expect(result.blob.type).toBe("application/zip");
    expect(result.blob.size).toBe("zipbytes".length); // decoded from base64

    const [url, opts] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe("/api/run");
    expect(JSON.parse((opts as RequestInit).body as string)).toEqual(PARAMS);
  });

  it("throws when the stream carries an error event", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        streamResponse([
          { type: "progress", message: "📥 Collecting…" },
          { type: "error", message: "fetch failed (exit 1): bad key" },
        ]),
      ),
    );

    await expect(runAnalysis(PARAMS, { onProgress: () => {} })).rejects.toThrow(
      "fetch failed (exit 1): bad key",
    );
  });

  it("throws with the server detail on a non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 429,
        body: null,
        json: async () => ({ detail: "Rate limit exceeded. Try again later." }),
      }),
    );

    await expect(runAnalysis(PARAMS, { onProgress: () => {} })).rejects.toThrow(/rate limit/i);
  });
});
