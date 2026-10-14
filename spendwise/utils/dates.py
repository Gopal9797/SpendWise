"""Date utility helpers."""

from datetime import date, datetime

from spendwise.config import DATE_INPUT_FORMAT, MONTH_KEY_FORMAT


def parse_date(value: str) -> date:
    """Parse a YYYY-MM-DD date value."""
    try:
        return datetime.strptime(value, DATE_INPUT_FORMAT).date()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid date '{value}'. Expected YYYY-MM-DD.") from exc


def month_key_from_date(value: date | str) -> str:
    if isinstance(value, str):
        parsed = parse_date(value)
    else:
        parsed = value
    return parsed.strftime(MONTH_KEY_FORMAT)


def parse_month_key(month_key: str) -> date:
    """Parse YYYY-MM and return the first day of month."""
    try:
        return datetime.strptime(month_key, MONTH_KEY_FORMAT).date()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid month '{month_key}'. Expected YYYY-MM.") from exc


def month_range(month_key: str) -> tuple[str, str]:
    """Return start and end ISO dates for a month key."""
    start = parse_month_key(month_key)
    if start.month == 12:
        end = date(start.year + 1, 1, 1)
    else:
        end = date(start.year, start.month + 1, 1)

    return start.isoformat(), end.isoformat()
