# Security Policy

## Supported versions

This is an actively developed personal project; only the latest commit on the
default branch is supported. Fixes are applied there rather than backported.

| Version            | Supported |
| ------------------ | --------- |
| Latest `main`      | ✅        |
| Older commits/tags | ❌        |

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

Report privately through GitHub's **[private vulnerability reporting](https://github.com/mpaloulack/training-analyzer/security/advisories/new)**
(Security tab → "Report a vulnerability"). Include:

- a description of the issue and its impact,
- the affected component (analyzer scripts, web backend, or frontend),
- steps to reproduce or a proof of concept,
- any suggested remediation.

You can expect an acknowledgement within a few days. Once a fix is ready it will
be released on `main` and the advisory published with credit, unless you prefer
to remain anonymous.

## Scope

This repository has three dependency surfaces, all watched by Dependabot:

- **Python** — the analyzer scripts (`requirements.txt`) and the web backend
  (`web/backend/requirements*.txt`, FastAPI/uvicorn).
- **JavaScript / React** — the frontend (`web/frontend`) and the Playwright E2E
  suite (`web/e2e`).
- **Docker** — the backend and frontend images (`web/*/Dockerfile`).

### Especially relevant

The web app accepts a user's **Intervals.icu API key** to run an analysis. By
design it is handled transiently:

- the key is passed only as a subprocess environment variable and is never
  written to disk or logged (it is also scrubbed from request object `repr`),
- each run uses a throwaway temp directory removed when the response ends,
- the result is streamed/returned in memory; nothing is persisted server-side.

Reports about credential leakage, log exposure, command injection, SSRF,
container escape, or weakening of these guarantees are in scope and very
welcome.

### Out of scope

- Vulnerabilities in Intervals.icu or other upstream services themselves.
- Findings that require a pre-compromised host or physical access.
- Missing hardening on a deployment you control (TLS, auth, network limits) —
  see the deployment notes in `web/README.md`; operators are responsible for
  running the stack behind HTTPS and tuning the rate limits.
