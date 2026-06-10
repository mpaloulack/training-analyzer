"""Request validation.

Validation does double duty here: it rejects nonsense early, and it constrains
every field that could otherwise be abused. Even though the runner passes
arguments as a list (no shell), we still bound dates, ids and physiology so a
caller can't drive the analyzer into a huge date range or inject odd strings.
"""
from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator

# An Intervals.icu athlete id is digits only (e.g. 882231 — no leading "i").
ATHLETE_ID_RE = r"^\d{3,9}$"
# API keys are short alphanumeric tokens; allow - and _ defensively.
API_KEY_RE = r"^[A-Za-z0-9_\-]{8,128}$"

MAX_RANGE_DAYS = 800  # ~26 months; the analyzer's default window is 6 months.


class RunParams(BaseModel):
    model_config = {"extra": "forbid"}

    athlete_id: str = Field(pattern=ATHLETE_ID_RE)
    api_key: str = Field(pattern=API_KEY_RE)
    start: date
    end: date
    fcm: int = Field(default=196, ge=120, le=240)
    lthr: int = Field(default=181, ge=100, le=230)
    fetch_intervals: bool = False

    @field_validator("athlete_id")
    @classmethod
    def strip_leading_i(cls, v: str) -> str:
        return v

    @model_validator(mode="after")
    def check_ranges(self) -> "RunParams":
        if self.end < self.start:
            raise ValueError("end date must not be before start date")
        if (self.end - self.start).days > MAX_RANGE_DAYS:
            raise ValueError(f"date range must not exceed {MAX_RANGE_DAYS} days")
        if self.lthr >= self.fcm:
            raise ValueError("lthr must be below fcm")
        return self

    def __repr__(self) -> str:  # never let the key leak into logs/tracebacks
        return (
            f"RunParams(athlete_id={self.athlete_id!r}, api_key='***', "
            f"start={self.start}, end={self.end}, fcm={self.fcm}, "
            f"lthr={self.lthr}, fetch_intervals={self.fetch_intervals})"
        )

    __str__ = __repr__
