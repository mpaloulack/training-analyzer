"""Runtime configuration, read once from the environment.

Nothing here is user data — only operational knobs. Secrets (the
Intervals.icu API key) are never stored; they flow straight from the request
into the subprocess environment and are dropped when the request ends.
"""
import os
from pathlib import Path


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


# Directory holding the analyzer script (fetch_training_data.py).
SCRIPTS_DIR = Path(os.environ.get("SCRIPTS_DIR", "/opt/scripts")).resolve()

# Comma-separated list of allowed CORS origins. Empty disables cross-origin.
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]

# Hard ceiling on how long the analyzer subprocesses may run (seconds).
RUN_TIMEOUT = _int("RUN_TIMEOUT", 240)

# Max number of analyses running at once (each spawns a Python subprocess + network).
MAX_CONCURRENCY = _int("MAX_CONCURRENCY", 2)

# Per-IP rate limit for the run endpoint.
RATE_LIMIT = os.environ.get("RATE_LIMIT", "5/hour")

# Test/CI hook: skip the real network fetch + plotting and emit a tiny stub package.
MOCK_FETCH = os.environ.get("MOCK_FETCH", "0") == "1"
