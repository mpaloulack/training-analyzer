import os
from pathlib import Path

import pytest

# Point the runner at the real analyzer scripts (repo root, two levels up).
REPO_ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("SCRIPTS_DIR", str(REPO_ROOT))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def min_json() -> Path:
    return FIXTURES / "training_data.min.json"
