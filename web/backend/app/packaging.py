"""Read the finished workspace's output for download.

Returns the bytes of training_data.json. Reading into memory keeps the
response self-contained; nothing is persisted beyond the request.
"""
from pathlib import Path


def read_output(workdir: Path) -> bytes:
    return (workdir / "training_data.json").read_bytes()
