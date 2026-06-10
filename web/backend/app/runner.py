"""Run the analyzer scripts in a throwaway workspace.

The contract: given validated params and an empty directory, produce
``training_data.json`` and ``graphs/*.png`` inside it. Secrets are passed only
through the subprocess environment of the fetch step and never written down.
The caller owns the directory's lifetime and deletes it afterwards.
"""
import subprocess
import sys
import threading
from collections.abc import Iterator
from pathlib import Path

from . import config
from .models import RunParams


class RunError(RuntimeError):
    """Raised when an analyzer step fails or times out."""


def build_fetch_cmd(params: RunParams, out_json: Path) -> list[str]:
    cmd = [
        sys.executable,
        str(config.SCRIPTS_DIR / "fetch_training_data.py"),
        "--start", params.start.isoformat(),
        "--end", params.end.isoformat(),
        "--fcm", str(params.fcm),
        "--lthr", str(params.lthr),
        "--out", str(out_json),
    ]
    if params.fetch_intervals:
        cmd.append("--fetch-intervals")
    return cmd


def build_plot_cmd(in_json: Path, graphs_dir: Path) -> list[str]:
    return [
        sys.executable,
        str(config.SCRIPTS_DIR / "plot_training.py"),
        str(in_json),
        "--out", str(graphs_dir),
    ]


_BASE_ENV = {
    "MPLBACKEND": "Agg",  # headless matplotlib
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/tmp",
    "PYTHONUNBUFFERED": "1",  # flush prints line-by-line so progress streams live
}


def fetch_env(params: RunParams) -> dict[str, str]:
    """Minimal environment for the fetch step. The API key lives only here."""
    return {
        "INTERVALS_ATHLETE_ID": params.athlete_id,
        "INTERVALS_API_KEY": params.api_key,
        **_BASE_ENV,
    }


def plot_env() -> dict[str, str]:
    return dict(_BASE_ENV)


def _run_step(cmd: list[str], cwd: Path, env: dict[str, str], label: str) -> None:
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, env=env, timeout=config.RUN_TIMEOUT,
            capture_output=True, text=True, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RunError(f"{label} timed out after {config.RUN_TIMEOUT}s") from exc
    if proc.returncode != 0:
        # stderr from these scripts is user-facing guidance, not secret-bearing.
        detail = (proc.stderr or proc.stdout or "").strip()[-2000:]
        raise RunError(f"{label} failed (exit {proc.returncode}): {detail}")


def run(params: RunParams, workdir: Path) -> None:
    """Populate ``workdir`` with training_data.json and graphs/ (non-streaming)."""
    out_json = workdir / "training_data.json"
    graphs_dir = workdir / "graphs"
    graphs_dir.mkdir(parents=True, exist_ok=True)

    if config.MOCK_FETCH:
        _write_stub(out_json, graphs_dir)
        return

    _run_step(build_fetch_cmd(params, out_json), workdir, fetch_env(params), "fetch")
    _run_step(build_plot_cmd(out_json, graphs_dir), workdir, plot_env(), "plot")


def _stream_step(
    cmd: list[str], cwd: Path, env: dict[str, str], label: str
) -> Iterator[str]:
    """Run a step and yield its stdout lines as they arrive.

    stderr is merged into stdout so the user sees errors inline. A watchdog
    timer kills the process past the timeout. Raises RunError on failure.
    """
    proc = subprocess.Popen(
        cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    timed_out = threading.Event()

    def _kill():
        timed_out.set()
        proc.kill()

    timer = threading.Timer(config.RUN_TIMEOUT, _kill)
    timer.start()
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip("\n")
            if line.strip():
                yield line
        proc.wait()
    finally:
        timer.cancel()
        if proc.poll() is None:
            proc.kill()

    if timed_out.is_set():
        raise RunError(f"{label} timed out after {config.RUN_TIMEOUT}s")
    if proc.returncode != 0:
        raise RunError(f"{label} failed (exit {proc.returncode})")


def run_streaming(params: RunParams, workdir: Path) -> Iterator[dict]:
    """Populate ``workdir`` while yielding {"type","message"} progress events."""
    out_json = workdir / "training_data.json"
    graphs_dir = workdir / "graphs"
    graphs_dir.mkdir(parents=True, exist_ok=True)

    if config.MOCK_FETCH:
        yield {"type": "progress", "message": "Mock mode: generating sample package…"}
        _write_stub(out_json, graphs_dir)
        return

    yield {"type": "progress", "message": "📥 Collecting data from Intervals.icu…"}
    for line in _stream_step(build_fetch_cmd(params, out_json), workdir, fetch_env(params), "fetch"):
        yield {"type": "progress", "message": line}

    yield {"type": "progress", "message": "🎨 Generating graphs…"}
    for line in _stream_step(build_plot_cmd(out_json, graphs_dir), workdir, plot_env(), "plot"):
        yield {"type": "progress", "message": line}

    yield {"type": "progress", "message": "📦 Packaging your download…"}


def _write_stub(out_json: Path, graphs_dir: Path) -> None:
    """Deterministic tiny output for E2E/CI without network or credentials."""
    out_json.write_text('{"meta": {"mock": true}, "activities": [], "wellness_timeline": []}')
    # 1x1 transparent PNG.
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c6360000002000154a24f9b0000000049454e44ae426082"
    )
    (graphs_dir / "1_fcm_vs_allure.png").write_bytes(png)
