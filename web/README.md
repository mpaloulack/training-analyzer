# Training Analyzer — Web

A small web app that lets other people run the Training Analyzer scripts
without touching a terminal or an `.env` file. They fill a form with their
Intervals.icu credentials and analysis parameters, the backend runs
`fetch_training_data.py` + `plot_training.py`, and they download a zip with
`training_data.json` and the five graphs.

**Live progress.** The backend streams each script's stdout to the browser as
newline-delimited JSON over the same POST, so users watch the same progress
they'd see in a terminal (`1/3 Activités…`, `100/130`, `✓ 1_fcm_vs_allure.png`,
…). The closing JSON line carries the zip (base64) and triggers the download —
no server-side job store, still fully stateless.

**Nothing is persisted.** The API key is used only as a subprocess environment
variable for one run and is never written to disk or logged. Each request runs
in a throwaway temp directory that is deleted as soon as the response is sent.

## Architecture

```
browser ──▶ frontend (nginx, :8080) ──/api/──▶ backend (FastAPI, :8000)
                                                   └─▶ fetch_training_data.py
                                                   └─▶ plot_training.py
```

- **frontend/** — React + TypeScript (Vite), built to static files served by
  an unprivileged nginx that also proxies `/api` to the backend.
- **backend/** — FastAPI. One endpoint, `POST /api/run`, validates input, runs
  the analyzer scripts in an isolated temp dir, and streams back a zip.
- The analyzer scripts live in the repo root and are copied into the backend
  image at build time — single source of truth, no vendored copies.

## Run it

```bash
cd web
cp .env.example .env        # optional — tweak port / limits
docker compose up --build
# open http://localhost:8080
```

Users get their **Athlete ID** and **API key** from
<https://intervals.icu/settings> (bottom of the page, "API" section).

## Security measures

- **No persistence of secrets**: API key flows request → subprocess env →
  discarded. It is excluded from `RunParams.__repr__`/`__str__` so it can't
  leak into logs or tracebacks. Output zip is built in memory.
- **Ephemeral workspace**: `tempfile.mkdtemp` per request, `rmtree` in a
  `finally` block.
- **Strict input validation** (`models.py`): athlete id and key are regex-bound,
  dates are real dates with a bounded range, physiology values are clamped,
  unknown fields are rejected.
- **No shell**: subprocesses are invoked with an argument list, never a shell
  string, and with a minimal environment (no inherited host vars).
- **Rate limiting** (`RATE_LIMIT`, default 5/hour/IP) and a **concurrency cap**
  (`MAX_CONCURRENCY`, default 2) with a 503 when busy.
- **Timeouts** (`RUN_TIMEOUT`, default 240s) kill runaway runs.
- **Hardened containers**: non-root users, `read_only` rootfs, `cap_drop: ALL`,
  `no-new-privileges`, tmpfs for scratch, backend not published (only the proxy
  reaches it), nginx body-size limit, and security headers (CSP, nosniff,
  X-Frame-Options, Referrer-Policy) on both the app and the API.

## Tests

```bash
# Backend unit + integration (validation, runner, packaging, API, real plotting)
cd backend && uv venv --python 3.12 .venv && . .venv/bin/activate
uv pip install -r requirements-dev.txt && pytest

# Frontend unit (form behavior, api client)
cd frontend && npm install && npm test

# E2E (full stack, no credentials needed)
MOCK_FETCH=1 docker compose up --build -d
cd e2e && npm install && npx playwright install --with-deps chromium
E2E_BASE_URL=http://localhost:8080 npx playwright test
docker compose down
```

`MOCK_FETCH=1` makes the backend skip the real network fetch + matplotlib and
emit a tiny deterministic zip, so E2E/CI runs without Intervals.icu credentials.
