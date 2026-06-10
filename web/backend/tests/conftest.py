import os
from pathlib import Path

# Point the runner at the real analyzer script (repo root, two levels up).
REPO_ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("SCRIPTS_DIR", str(REPO_ROOT))
