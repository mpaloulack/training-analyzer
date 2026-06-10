import pytest
from pydantic import ValidationError

from app.models import RunParams

VALID = dict(
    athlete_id="882231",
    api_key="abcd1234efgh5678",
    start="2026-01-01",
    end="2026-03-01",
)


def test_accepts_valid_input_with_defaults():
    p = RunParams(**VALID)
    assert p.fcm == 196 and p.lthr == 181 and p.fetch_intervals is False


@pytest.mark.parametrize("athlete_id", ["i882231", "abc", "", "12", "1" * 10])
def test_rejects_bad_athlete_id(athlete_id):
    with pytest.raises(ValidationError):
        RunParams(**{**VALID, "athlete_id": athlete_id})


@pytest.mark.parametrize("api_key", ["short", "", "has space", "bad$char!!!"])
def test_rejects_bad_api_key(api_key):
    with pytest.raises(ValidationError):
        RunParams(**{**VALID, "api_key": api_key})


def test_rejects_end_before_start():
    with pytest.raises(ValidationError):
        RunParams(**{**VALID, "start": "2026-03-01", "end": "2026-01-01"})


def test_rejects_oversized_range():
    with pytest.raises(ValidationError):
        RunParams(**{**VALID, "start": "2020-01-01", "end": "2026-01-01"})


def test_rejects_lthr_not_below_fcm():
    with pytest.raises(ValidationError):
        RunParams(**{**VALID, "fcm": 180, "lthr": 181})


@pytest.mark.parametrize("field,value", [("fcm", 300), ("lthr", 50)])
def test_rejects_out_of_range_physiology(field, value):
    with pytest.raises(ValidationError):
        RunParams(**{**VALID, field: value})


def test_rejects_unknown_field():
    with pytest.raises(ValidationError):
        RunParams(**{**VALID, "evil": "x"})


def test_api_key_never_in_repr():
    p = RunParams(**VALID)
    assert "abcd1234efgh5678" not in repr(p)
    assert "abcd1234efgh5678" not in str(p)
