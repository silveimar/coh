"""Naive UTC clock for domain timestamp defaults.

JSON columns store datetimes with isoformat(), so a naive value keeps newly
stored strings free of a UTC offset, the same form as before.
"""

from datetime import UTC, datetime


def utc_now_naive() -> datetime:
    """Return the current UTC wall-clock time without tzinfo."""
    return datetime.now(UTC).replace(tzinfo=None)
