"""Exercises the real plot_training.py against an anonymized fixture.

This is the only test that runs matplotlib for real, proving the analyzer's
plotting path still produces the expected PNGs. Skips cleanly if matplotlib or
the script isn't available (e.g. a minimal CI image).
"""
import shutil

import pytest

from app import config, runner

pytest.importorskip("matplotlib")

PLOT_SCRIPT = config.SCRIPTS_DIR / "plot_training.py"
pytestmark = pytest.mark.skipif(not PLOT_SCRIPT.is_file(), reason="plot_training.py not found")


def test_plot_produces_pngs(tmp_path, min_json):
    shutil.copy(min_json, tmp_path / "training_data.json")
    graphs = tmp_path / "graphs"
    graphs.mkdir()
    cmd = runner.build_plot_cmd(tmp_path / "training_data.json", graphs)
    runner._run_step(cmd, tmp_path, {"MPLBACKEND": "Agg", "PATH": "/usr/bin:/bin", "HOME": "/tmp"}, "plot")

    pngs = list(graphs.glob("*.png"))
    assert pngs, "expected at least one generated graph"
    assert all(p.stat().st_size > 0 for p in pngs)
