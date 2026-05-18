import xml.etree.ElementTree as ET
from datetime import date, datetime

import requests

TALLY_HOST = "localhost"
TALLY_PORT = 9000
TALLY_TIMEOUT = 30

_DATE_FORMATS = ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d%m%Y", "%d-%b-%Y"]


def build_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def parse_date_arg(s: str) -> date:
    s = s.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        f"Invalid date: {s!r}. Accepted formats: DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD, DD-Mon-YYYY"
    )


def format_amount(raw: str) -> str:
    try:
        val = float(raw.replace(",", "").strip())
        return f"{abs(val):,.2f}"
    except ValueError:
        return raw.strip()


def _parse_tally_date(raw: str) -> str:
    raw = raw.strip()
    for fmt in ("%Y%m%d", "%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%d-%m-%Y")
        except ValueError:
            continue
    return raw


def _safe_text(element: ET.Element | None, default: str = "") -> str:
    if element is None:
        return default
    return (element.text or "").strip()
