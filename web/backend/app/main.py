"""FastAPI entrypoint: one endpoint that runs the analyzer and streams a zip.

Stateless by construction — every request gets a fresh temp dir that is removed
in a finally block, and no request data is logged or persisted.
"""
import base64
import json
import shutil
import tempfile
import threading
from collections.abc import Iterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from . import config, packaging, runner
from .models import RunParams

limiter = Limiter(key_func=get_remote_address)
# threading.Semaphore: the run executes inside a sync streaming generator that
# Starlette iterates in a worker thread, so the guard must be thread-based.
_semaphore = threading.Semaphore(config.MAX_CONCURRENCY)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not config.MOCK_FETCH and not config.SCRIPTS_DIR.is_dir():
        raise RuntimeError(f"SCRIPTS_DIR not found: {config.SCRIPTS_DIR}")
    yield


app = FastAPI(title="Training Analyzer", docs_url=None, redoc_url=None, lifespan=lifespan)
app.state.limiter = limiter

if config.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_methods=["POST", "GET"],
        allow_headers=["Content-Type"],
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again later."})


@app.get("/api/health")
async def health():
    return {"status": "ok", "mock": config.MOCK_FETCH}


def _ndjson(event: dict) -> str:
    return json.dumps(event) + "\n"


def _stream_run(params: RunParams) -> Iterator[str]:
    """Yield NDJSON progress events, then a final event carrying the zip.

    Stateless: a fresh temp dir per request, always removed; the API key never
    leaves the subprocess env; the zip is base64'd into the closing event so
    nothing is held server-side after the response ends.
    """
    if not _semaphore.acquire(blocking=False):
        yield _ndjson({"type": "error", "message": "Server busy, retry shortly."})
        return

    workdir = Path(tempfile.mkdtemp(prefix="ta_"))
    try:
        try:
            for event in runner.run_streaming(params, workdir):
                yield _ndjson(event)
            data = packaging.build_zip(workdir)
        except runner.RunError as exc:
            yield _ndjson({"type": "error", "message": str(exc)})
            return
        yield _ndjson({
            "type": "done",
            "filename": "training-analysis.zip",
            "zip_b64": base64.b64encode(data).decode("ascii"),
        })
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
        _semaphore.release()


@app.post("/api/run")
@limiter.limit(config.RATE_LIMIT)
async def run_analysis(request: Request, params: RunParams):
    return StreamingResponse(
        _stream_run(params),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
