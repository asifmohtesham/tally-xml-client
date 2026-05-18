#!/usr/bin/env python3
"""
TallyPrime Sales Voucher Lister
Connects to a local TallyPrime Gold server via its XML HTTP gateway
and lists Sales Vouchers for a specified date range.

Requirements:
  pip install requests

TallyPrime setup:
  Gateway of Tally > F12 (Configure) > Advanced Configuration
  Enable TallyPrime to act as HTTP Server on port 9000 (default).
"""

import argparse
import sys
import textwrap
import xml.etree.ElementTree as ET
from datetime import date, datetime

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: run  pip install requests")


TALLY_HOST = "localhost"
TALLY_PORT = 9000
TALLY_URL  = f"http://{TALLY_HOST}:{TALLY_PORT}"
TALLY_TIMEOUT = 30  # seconds


# ---------------------------------------------------------------------------
# XML request builders
# ---------------------------------------------------------------------------

def _xml_company_info() -> str:
    """Fetch the active company name — used as a connectivity check."""
    return """<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>List of Companies</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


def _xml_sales_vouchers(from_date: date, to_date: date) -> str:
    """
    Build the TDL collection request for Sales Vouchers.

    Uses an inline TDL COLLECTION filtered to vouchertype = "Sales",
    bounded by SVFROMDATE / SVTODATE so Tally applies the date window
    server-side before returning results.
    """
    fd = from_date.strftime("%Y%m%d")
    td = to_date.strftime("%Y%m%d")
    return f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>$$CollectionName:PyTallySalesVouchers</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <SVFROMDATE>{fd}</SVFROMDATE>
          <SVTODATE>{td}</SVTODATE>
        </STATICVARIABLES>
        <TDLMESSAGE>
          <COLLECTION NAME="PyTallySalesVouchers" ISMODIFY="No">
            <TYPE>Voucher</TYPE>
            <FILTER>PyIsSalesVoucher</FILTER>
          </COLLECTION>
          <SYSTEM TYPE="Formulae" NAME="PyIsSalesVoucher">
            $$VoucherTypeName = "Sales"
          </SYSTEM>
        </TDLMESSAGE>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _post_xml(xml_body: str, url: str = TALLY_URL) -> ET.Element:
    """POST XML to the Tally gateway and return the parsed root element."""
    headers = {
        "Content-Type": "text/xml;charset=utf-8",
        "Content-Length": str(len(xml_body.encode("utf-8"))),
    }
    try:
        resp = requests.post(url, data=xml_body.encode("utf-8"),
                             headers=headers, timeout=TALLY_TIMEOUT)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        sys.exit(
            f"Cannot reach TallyPrime at {url}.\n"
            "Ensure TallyPrime is running and the HTTP server is enabled on port 9000:\n"
            "  Gateway of Tally > F12 > Advanced Configuration > Enable HTTP Server"
        )
    except requests.exceptions.Timeout:
        sys.exit(f"Request timed out after {TALLY_TIMEOUT}s. TallyPrime may be busy.")
    except requests.exceptions.HTTPError as exc:
        sys.exit(f"HTTP error: {exc}")

    try:
        return ET.fromstring(resp.content)
    except ET.ParseError as exc:
        sys.exit(f"Could not parse Tally response as XML: {exc}\n"
                 f"Raw response (first 500 chars):\n{resp.text[:500]}")


# ---------------------------------------------------------------------------
# Company / connectivity check
# ---------------------------------------------------------------------------

def check_connection_and_get_company(url: str) -> str:
    """Return the active company name, or exit with an error."""
    root = _post_xml(_xml_company_info(), url)
    # Tally returns <COMPANY> elements; grab NAME of the first one
    for company in root.iter("COMPANY"):
        name = company.findtext("NAME") or company.get("NAME", "")
        if name:
            return name
    # Fallback: some versions embed it differently
    name = root.findtext(".//COMPANYNAME") or root.findtext(".//NAME") or "Unknown"
    return name


# ---------------------------------------------------------------------------
# Voucher parsing
# ---------------------------------------------------------------------------

def _safe_text(element: ET.Element | None, default: str = "") -> str:
    if element is None:
        return default
    return (element.text or "").strip()


def _parse_tally_date(raw: str) -> str:
    """Convert TallyPrime date (YYYYMMDD or DD-Mon-YYYY) to DD-MM-YYYY."""
    raw = raw.strip()
    for fmt in ("%Y%m%d", "%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%d-%m-%Y")
        except ValueError:
            continue
    return raw  # return as-is if nothing matched


def _format_amount(raw: str) -> str:
    """Tally stores debit amounts as negative for sales; show absolute value."""
    try:
        val = float(raw.replace(",", "").strip())
        return f"{abs(val):,.2f}"
    except ValueError:
        return raw.strip()


def parse_vouchers(root: ET.Element) -> list[dict]:
    """Extract Sales Voucher rows from the Tally XML envelope."""
    vouchers = []
    for voucher in root.iter("VOUCHER"):
        vtype = (_safe_text(voucher.find("VOUCHERTYPENAME"))
                 or voucher.get("VCHTYPE", "")).strip()

        # Guard: only keep Sales (collection filter should already do this)
        if vtype.lower() != "sales":
            continue

        row = {
            "date":         _parse_tally_date(_safe_text(voucher.find("DATE"))),
            "voucher_no":   _safe_text(voucher.find("VOUCHERNUMBER")),
            "party":        _safe_text(voucher.find("PARTYLEDGERNAME")),
            "amount":       _format_amount(_safe_text(voucher.find("AMOUNT"))),
            "narration":    _safe_text(voucher.find("NARRATION")),
            "reference":    _safe_text(voucher.find("REFERENCE")),
            "vch_type":     vtype,
        }
        vouchers.append(row)

    # Sort chronologically, then by voucher number
    vouchers.sort(key=lambda v: (v["date"], v["voucher_no"]))
    return vouchers


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

COL_WIDTHS = {
    "date":       10,
    "voucher_no": 14,
    "party":      30,
    "amount":     14,
    "narration":  28,
    "reference":  14,
}

HEADERS = {
    "date":       "Date",
    "voucher_no": "Voucher No.",
    "party":      "Party Name",
    "amount":     "Amount (₹)",
    "narration":  "Narration",
    "reference":  "Ref / Order No.",
}

DISPLAY_COLS = ["date", "voucher_no", "party", "amount", "reference", "narration"]


def _cell(value: str, width: int, right_align: bool = False) -> str:
    truncated = value[:width - 1] + "…" if len(value) > width else value
    return truncated.rjust(width) if right_align else truncated.ljust(width)


def print_vouchers(vouchers: list[dict], from_date: date, to_date: date,
                   company: str) -> None:
    sep = "  "
    header_line = sep.join(
        _cell(HEADERS[c], COL_WIDTHS[c], right_align=(c == "amount"))
        for c in DISPLAY_COLS
    )
    divider = sep.join("-" * COL_WIDTHS[c] for c in DISPLAY_COLS)

    total_width = len(divider)
    title = (f"Sales Vouchers  |  {company}  |  "
             f"{from_date.strftime('%d-%m-%Y')} to {to_date.strftime('%d-%m-%Y')}")

    print()
    print(title.center(total_width))
    print("=" * total_width)
    print(header_line)
    print(divider)

    grand_total = 0.0
    for v in vouchers:
        print(sep.join(
            _cell(v[c], COL_WIDTHS[c], right_align=(c == "amount"))
            for c in DISPLAY_COLS
        ))
        try:
            grand_total += float(v["amount"].replace(",", ""))
        except ValueError:
            pass

    print(divider)
    total_label = f"Total  ({len(vouchers)} voucher{'s' if len(vouchers) != 1 else ''})"
    total_amount = f"{grand_total:,.2f}"
    summary_parts = []
    for c in DISPLAY_COLS:
        if c == "party":
            summary_parts.append(_cell(total_label, COL_WIDTHS[c]))
        elif c == "amount":
            summary_parts.append(_cell(total_amount, COL_WIDTHS[c], right_align=True))
        else:
            summary_parts.append(" " * COL_WIDTHS[c])
    print(sep.join(summary_parts))
    print()


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

DATE_FORMATS = ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d%m%Y", "%d-%b-%Y"]


def parse_date_arg(s: str, label: str = "date") -> date:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    sys.exit(
        f"Invalid {label}: {s!r}\n"
        f"Accepted formats: DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD, DD-Mon-YYYY"
    )


def prompt_date(prompt_text: str) -> date:
    while True:
        raw = input(prompt_text).strip()
        if not raw:
            continue
        try:
            return parse_date_arg(raw, "date")
        except SystemExit as exc:
            print(exc)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tally_sales_vouchers",
        description="List Sales Vouchers from a local TallyPrime Gold server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python tally_sales_vouchers.py                              # interactive prompts
              python tally_sales_vouchers.py -f 01-04-2025 -t 31-03-2026
              python tally_sales_vouchers.py -f 01-04-2025 -t 31-03-2026 --host 192.168.1.10
              python tally_sales_vouchers.py -f 01-04-2025 -t 31-03-2026 --host 192.168.1.10 --port 9002
              python tally_sales_vouchers.py -f 01-04-2025 -t 31-03-2026 --url http://tally.local:9000
        """),
    )
    p.add_argument("-f", "--from-date", metavar="DATE",
                   help="Start date  (DD-MM-YYYY | DD/MM/YYYY | YYYY-MM-DD)")
    p.add_argument("-t", "--to-date", metavar="DATE",
                   help="End date    (DD-MM-YYYY | DD/MM/YYYY | YYYY-MM-DD)")

    conn = p.add_argument_group(
        "server connection",
        "Use --host / --port for simple setups, or --url for full control. "
        "--url takes precedence when all three are provided.",
    )
    conn.add_argument("--host", default=TALLY_HOST, metavar="HOST",
                      help=f"TallyPrime server hostname or IP  (default: {TALLY_HOST})")
    conn.add_argument("--port", default=TALLY_PORT, metavar="PORT", type=int,
                      help=f"TallyPrime HTTP gateway port       (default: {TALLY_PORT})")
    conn.add_argument("--url", default=None, metavar="URL",
                      help="Full gateway URL — overrides --host and --port")

    p.add_argument("--no-narration", action="store_true",
                   help="Hide the Narration column")
    return p


def resolve_url(args: argparse.Namespace) -> str:
    """Return the effective gateway URL from parsed arguments."""
    if args.url:
        return args.url.rstrip("/")
    if args.port < 1 or args.port > 65535:
        sys.exit(f"Invalid port: {args.port}. Must be between 1 and 65535.")
    return f"http://{args.host}:{args.port}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = build_parser().parse_args()

    # Resolve date range
    if args.from_date:
        from_date = parse_date_arg(args.from_date, "from-date")
    else:
        from_date = prompt_date("From date (DD-MM-YYYY): ")

    if args.to_date:
        to_date = parse_date_arg(args.to_date, "to-date")
    else:
        to_date = prompt_date("To   date (DD-MM-YYYY): ")

    if from_date > to_date:
        sys.exit(f"from-date ({from_date}) must not be later than to-date ({to_date}).")

    url = resolve_url(args)

    # Connectivity check
    print(f"\nConnecting to TallyPrime at {url} …", end=" ", flush=True)
    company = check_connection_and_get_company(url)
    print(f"OK  [{company}]")

    # Fetch vouchers
    print("Fetching Sales Vouchers …", end=" ", flush=True)
    xml_request = _xml_sales_vouchers(from_date, to_date)
    root = _post_xml(xml_request, url)
    vouchers = parse_vouchers(root)
    print(f"found {len(vouchers)}.")

    if not vouchers:
        print(f"\nNo Sales Vouchers found between "
              f"{from_date.strftime('%d-%m-%Y')} and {to_date.strftime('%d-%m-%Y')}.")
        return

    if args.no_narration and "narration" in DISPLAY_COLS:
        DISPLAY_COLS.remove("narration")

    print_vouchers(vouchers, from_date, to_date, company)


if __name__ == "__main__":
    main()
