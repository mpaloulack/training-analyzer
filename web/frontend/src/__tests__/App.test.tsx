import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";

afterEach(() => vi.restoreAllMocks());

function streamResponse(events: object[]) {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const e of events) controller.enqueue(encoder.encode(JSON.stringify(e) + "\n"));
      controller.close();
    },
  });
  return { ok: true, status: 200, body } as unknown as Response;
}

function stubStream(events: object[]) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(streamResponse(events)));
  vi.stubGlobal("URL", { createObjectURL: () => "blob:x", revokeObjectURL: () => {} });
}

async function fillCreds() {
  await userEvent.type(screen.getByLabelText("Athlete ID"), "882231");
  await userEvent.type(screen.getByLabelText("API key"), "abcd1234efgh5678");
}

describe("App form", () => {
  it("renders physiology defaults", () => {
    render(<App />);
    expect(screen.getByLabelText("FCM (max HR)")).toHaveValue(196);
    expect(screen.getByLabelText("LTHR (threshold HR)")).toHaveValue(181);
    expect(screen.getByLabelText("Fetch intervals")).toBeChecked();
  });

  it("blocks submit and shows error on invalid athlete id", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await userEvent.type(screen.getByLabelText("Athlete ID"), "nope");
    await userEvent.type(screen.getByLabelText("API key"), "abcd1234efgh5678");
    await userEvent.click(screen.getByRole("button"));

    expect(await screen.findByRole("alert")).toHaveTextContent(/athlete id/i);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows streamed progress and reports success", async () => {
    stubStream([
      { type: "progress", message: "1/3 Activités…" },
      { type: "progress", message: "🎨 Generating graphs…" },
      { type: "done", filename: "training-analysis.zip", zip_b64: btoa("zip") },
    ]);
    render(<App />);
    await fillCreds();
    await userEvent.click(screen.getByRole("button"));

    const log = await screen.findByLabelText("progress log");
    expect(log).toHaveTextContent("1/3 Activités");
    expect(log).toHaveTextContent("Generating graphs");
    expect(await screen.findByRole("status")).toHaveTextContent(/done/i);
  });

  it("surfaces a streamed error event", async () => {
    stubStream([
      { type: "progress", message: "📥 Collecting…" },
      { type: "error", message: "bad key" },
    ]);
    render(<App />);
    await fillCreds();
    await userEvent.click(screen.getByRole("button"));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("bad key"));
  });

  it("switches the UI to French and translates labels and errors", async () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<App />);

    await userEvent.selectOptions(screen.getByLabelText("Language"), "fr");

    // A label is translated.
    expect(screen.getByLabelText("Clé API")).toBeInTheDocument();
    // Validation message comes through in French.
    await userEvent.type(screen.getByLabelText("Athlete ID"), "nope");
    await userEvent.type(screen.getByLabelText("Clé API"), "abcd1234efgh5678");
    await userEvent.click(screen.getByRole("button", { name: /générer/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/Athlete ID/i);
  });
});
