from pathlib import Path

from app import runner
from app.models import RunParams

PARAMS = RunParams(
    athlete_id="882231", api_key="secretkey1234567",
    start="2026-01-01", end="2026-03-01", fcm=190, lthr=175, fetch_intervals=True,
)


def test_fetch_cmd_uses_validated_args():
    cmd = runner.build_fetch_cmd(PARAMS, Path("/tmp/out.json"))
    assert "--start" in cmd and "2026-01-01" in cmd
    assert "--fcm" in cmd and "190" in cmd
    assert "--fetch-intervals" in cmd


def test_fetch_cmd_omits_intervals_flag_when_disabled():
    p = PARAMS.model_copy(update={"fetch_intervals": False})
    assert "--fetch-intervals" not in runner.build_fetch_cmd(p, Path("/tmp/out.json"))


def test_secret_only_in_env_never_in_argv():
    cmd = runner.build_fetch_cmd(PARAMS, Path("/tmp/out.json"))
    assert "secretkey1234567" not in " ".join(cmd)
    env = runner.fetch_env(PARAMS)
    assert env["INTERVALS_API_KEY"] == "secretkey1234567"
    assert env["INTERVALS_ATHLETE_ID"] == "882231"


def test_fetch_env_is_minimal():
    env = runner.fetch_env(PARAMS)
    # No inherited environment that could leak host secrets into the subprocess.
    assert set(env) == {
        "INTERVALS_ATHLETE_ID", "INTERVALS_API_KEY",
        "MPLBACKEND", "PATH", "HOME", "PYTHONUNBUFFERED",
    }
    # Live streaming depends on unbuffered subprocess output.
    assert env["PYTHONUNBUFFERED"] == "1"


def test_mock_run_writes_stub_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.config, "MOCK_FETCH", True)
    runner.run(PARAMS, tmp_path)
    assert (tmp_path / "training_data.json").is_file()
    assert (tmp_path / "graphs" / "1_fcm_vs_allure.png").is_file()


def test_mock_streaming_yields_events_and_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.config, "MOCK_FETCH", True)
    events = list(runner.run_streaming(PARAMS, tmp_path))
    assert events and all(e["type"] == "progress" for e in events)
    assert (tmp_path / "training_data.json").is_file()
    assert (tmp_path / "graphs" / "1_fcm_vs_allure.png").is_file()
