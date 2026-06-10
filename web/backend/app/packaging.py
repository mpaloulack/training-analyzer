"""Zip a finished workspace into an in-memory download.

In-memory so the archive is never persisted to disk; the bytes live only for
the duration of the response.
"""
import io
import zipfile
from pathlib import Path


def build_zip(workdir: Path) -> bytes:
    json_path = workdir / "training_data.json"
    graphs_dir = workdir / "graphs"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if json_path.is_file():
            zf.write(json_path, "training_data.json")
        if graphs_dir.is_dir():
            for png in sorted(graphs_dir.glob("*.png")):
                zf.write(png, f"graphs/{png.name}")
    return buf.getvalue()
