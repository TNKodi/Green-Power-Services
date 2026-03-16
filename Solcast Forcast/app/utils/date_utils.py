"""Date parsing and validation helpers for forecast requests."""
from datetime import datetime
from typing import Tuple


def parse_iso_date(date_str: str) -> datetime:
    """Parse ISO-8601 date or datetime string.

    Accepts YYYY-MM-DD or full ISO timestamp. Raises ValueError on invalid input.
    """
    if not date_str or not isinstance(date_str, str):
        raise ValueError("Date string is required")
    try:
        return datetime.fromisoformat(date_str)
    except ValueError as exc:
        raise ValueError(f"Invalid date format: {date_str}") from exc


def validate_date_range(start_date: str, end_date: str) -> Tuple[datetime, datetime]:
    """Validate start/end dates and ensure chronological order."""
    start_dt = parse_iso_date(start_date)
    end_dt = parse_iso_date(end_date)

    if end_dt <= start_dt:
        raise ValueError("end_date must be later than start_date")

    return start_dt, end_dt
