from datetime import datetime
from dateutil import parser as date_parser


def parse_expiry(value) -> datetime | None:
    try:
        return date_parser.parse(str(value)) if value is not None else None
    except Exception:
        return None
