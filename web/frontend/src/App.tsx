import { type FormEvent, type ReactNode, useEffect, useState } from "react";
import { downloadBlob, runAnalysis, type RunParams } from "./api";
import { detectLang, saveLang, translations, type Lang } from "./i18n";

const today = new Date().toISOString().slice(0, 10);

const DEFAULTS: RunParams = {
  athlete_id: "",
  api_key: "",
  start: "2025-12-01",
  end: today,
  fcm: 196,
  lthr: 181,
  fetch_intervals: true,
};

type ErrKey = "errAthleteId" | "errApiKey" | "errDates" | "errLthr";

function validate(p: RunParams): ErrKey | null {
  if (!/^\d{3,9}$/.test(p.athlete_id)) return "errAthleteId";
  if (!/^[A-Za-z0-9_-]{8,128}$/.test(p.api_key)) return "errApiKey";
  if (p.end < p.start) return "errDates";
  if (p.lthr >= p.fcm) return "errLthr";
  return null;
}

export function App() {
  const [lang, setLang] = useState<Lang>(detectLang);
  const [form, setForm] = useState<RunParams>(DEFAULTS);
  const [status, setStatus] = useState<"idle" | "running" | "done">("idle");
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string[]>([]);

  const t = translations[lang];

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  function changeLang(next: Lang) {
    setLang(next);
    saveLang(next);
    setError(null); // re-render the (possibly shown) error in the new language on next submit
  }

  function update<K extends keyof RunParams>(key: K, value: RunParams[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const problem = validate(form);
    if (problem) {
      setError(t[problem]);
      return;
    }
    setStatus("running");
    setProgress([]);
    try {
      const { blob, filename } = await runAnalysis(form, {
        onProgress: (message) => setProgress((lines) => [...lines, message]),
      });
      downloadBlob(blob, filename);
      setStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : t.errUnexpected);
      setStatus("idle");
    }
  }

  return (
    <main style={{ maxWidth: 520, margin: "2rem auto", fontFamily: "system-ui, sans-serif" }}>
      <div style={{ textAlign: "right" }}>
        <select
          aria-label={t.languageLabel}
          value={lang}
          onChange={(e) => changeLang(e.target.value as Lang)}
        >
          <option value="en">English</option>
          <option value="fr">Français</option>
        </select>
      </div>

      <h1>Training Analyzer</h1>
      <p>{t.intro}</p>

      <details
        style={{
          background: "#f3f5f8",
          border: "1px solid #d9dee6",
          borderRadius: 6,
          padding: "0.75rem 1rem",
          margin: "1rem 0",
          fontSize: "0.9rem",
        }}
      >
        <summary style={{ cursor: "pointer", fontWeight: 600 }}>{t.helpSummary}</summary>
        <ol style={{ margin: "0.75rem 0 0", paddingLeft: "1.25rem", lineHeight: 1.5 }}>
          {t.helpSteps.map((step, i) => (
            <li key={i}>{step}</li>
          ))}
        </ol>
        <p style={{ margin: "0.75rem 0 0", color: "#555" }}>{t.helpPrivacy}</p>
      </details>

      <form onSubmit={onSubmit} aria-label="analysis form">
        <Field label={t.labelAthleteId}>
          <input
            aria-label={t.labelAthleteId}
            value={form.athlete_id}
            onChange={(e) => update("athlete_id", e.target.value)}
            required
          />
        </Field>
        <Field label={t.labelApiKey}>
          <input
            aria-label={t.labelApiKey}
            type="password"
            value={form.api_key}
            onChange={(e) => update("api_key", e.target.value)}
            required
          />
        </Field>
        <Field label={t.labelStart}>
          <input
            aria-label={t.labelStart}
            type="date"
            value={form.start}
            onChange={(e) => update("start", e.target.value)}
          />
        </Field>
        <Field label={t.labelEnd}>
          <input
            aria-label={t.labelEnd}
            type="date"
            value={form.end}
            onChange={(e) => update("end", e.target.value)}
          />
        </Field>
        <Field label={t.labelFcm}>
          <input
            aria-label={t.labelFcm}
            type="number"
            value={form.fcm}
            onChange={(e) => update("fcm", Number(e.target.value))}
          />
        </Field>
        <Field label={t.labelLthr}>
          <input
            aria-label={t.labelLthr}
            type="number"
            value={form.lthr}
            onChange={(e) => update("lthr", Number(e.target.value))}
          />
        </Field>
        <label style={{ display: "block", margin: "0.75rem 0" }}>
          <input
            type="checkbox"
            aria-label={t.ariaFetchIntervals}
            checked={form.fetch_intervals}
            onChange={(e) => update("fetch_intervals", e.target.checked)}
          />{" "}
          {t.textFetchIntervals}
        </label>

        <button type="submit" disabled={status === "running"}>
          {status === "running" ? t.submitRunning : t.submitIdle}
        </button>
      </form>

      {progress.length > 0 && (
        <pre
          aria-label={t.progressLogLabel}
          style={{
            background: "#0f1115",
            color: "#d6e2f0",
            padding: "0.75rem 1rem",
            borderRadius: 6,
            maxHeight: 240,
            overflowY: "auto",
            fontSize: "0.8rem",
            whiteSpace: "pre-wrap",
            marginTop: "1rem",
          }}
        >
          {progress.join("\n")}
        </pre>
      )}

      {error && (
        <p role="alert" style={{ color: "#b00020" }}>
          {error}
        </p>
      )}
      {status === "done" && (
        <p role="status" style={{ color: "#0a7d28" }}>
          {t.doneMsg}
        </p>
      )}
    </main>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label style={{ display: "block", margin: "0.5rem 0" }}>
      <span style={{ display: "block", fontSize: "0.85rem" }}>{label}</span>
      {children}
    </label>
  );
}
