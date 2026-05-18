# GUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `tally_sales_vouchers.py` into the `tally_xml_client` package and add a CustomTkinter GUI that coexists with the existing CLI.

**Architecture:** A `tally_xml_client/` package with `core.py` (pure logic), `cli.py` (terminal UI), and `gui.py` (CustomTkinter window). `main.py` at the repo root is the single entry point: no args → GUI, any arg → CLI.

**Tech Stack:** Python 3.10+, CustomTkinter, requests, pytest, unittest.mock

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `tally_xml_client/__init__.py` | Package marker, `__version__` |
| Create | `tally_xml_client/core.py` | HTTP, TDL XML, parsing, date utils — no side effects |
| Create | `tally_xml_client/cli.py` | argparse, table printing, catches `RuntimeError` → `sys.exit` |
| Create | `tally_xml_client/gui.py` | CustomTkinter window, settings persistence |
| Create | `main.py` | Launcher: routes to CLI or GUI |
| Create | `tests/__init__.py` | Test package marker |
| Create | `tests/test_core.py` | Unit tests for `core.py` |
| Delete | `tally_sales_vouchers.py` | Superseded by the package |
| Modify | `README.md` | Update install, usage, add GUI section |

---

## Task 1: Package skeleton and test infrastructure

**Files:**
- Create: `tally_xml_client/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create the package and tests directories**

```powershell
New-Item -ItemType Directory -Force tally_xml_client
New-Item -ItemType Directory -Force tests
```

- [ ] **Step 2: Write `tally_xml_client/__init__.py`**

```python
__version__ = "0.2.0"
```

- [ ] **Step 3: Write `tests/__init__.py`**

```python
```

(empty file — marks tests/ as a package)

- [ ] **Step 4: Install dependencies**

```powershell
pip install pytest customtkinter requests
```

Expected: all three install without error. `customtkinter` pulls in `tkinter` support automatically on Windows.

- [ ] **Step 5: Verify pytest discovers the tests directory**

```powershell
pytest tests/ --collect-only
```

Expected output contains: `<Module tests/__init__.py>` or `no tests ran` — either is fine at this stage.

- [ ] **Step 6: Commit**

```bash
git add tally_xml_client/__init__.py tests/__init__.py
git commit -m "feat: add tally_xml_client package skeleton and tests directory"
```

---

## Task 2: `core.py` — utility functions (TDD)

**Files:**
- Create: `tests/test_core.py` (utility function tests)
- Create: `tally_xml_client/core.py` (utility functions only)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_core.py`:

```python
import pytest
from datetime import date
from unittest.mock import patch, MagicMock
import xml.etree.ElementTree as ET
import requests as req_lib

from tally_xml_client import core


class TestBuildUrl:
    def test_localhost(self):
        assert core.build_url("localhost", 9000) == "http://localhost:9000"

    def test_ip_and_custom_port(self):
        assert core.build_url("192.168.1.10", 9002) == "http://192.168.1.10:9002"


class TestParseDateArg:
    def test_dd_mm_yyyy(self):
        assert core.parse_date_arg("01-04-2025") == date(2025, 4, 1)

    def test_dd_slash_mm_yyyy(self):
        assert core.parse_date_arg("01/04/2025") == date(2025, 4, 1)

    def test_yyyy_mm_dd(self):
        assert core.parse_date_arg("2025-04-01") == date(2025, 4, 1)

    def test_dd_mon_yyyy(self):
        assert core.parse_date_arg("01-Apr-2025") == date(2025, 4, 1)

    def test_invalid_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid date"):
            core.parse_date_arg("not-a-date")

    def test_strips_whitespace(self):
        assert core.parse_date_arg("  01-04-2025  ") == date(2025, 4, 1)


class TestFormatAmount:
    def test_negative_becomes_positive(self):
        assert core.format_amount("-45000.00") == "45,000.00"

    def test_strips_existing_commas_before_parsing(self):
        assert core.format_amount("1,12,500") == "112,500.00"

    def test_positive_passthrough(self):
        assert core.format_amount("45000") == "45,000.00"

    def test_invalid_returns_stripped_string(self):
        assert core.format_amount("  N/A  ") == "N/A"
```

- [ ] **Step 2: Run to confirm all fail**

```powershell
pytest tests/test_core.py::TestBuildUrl tests/test_core.py::TestParseDateArg tests/test_core.py::TestFormatAmount -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'tally_xml_client.core'`

- [ ] **Step 3: Create `tally_xml_client/core.py` with utility functions**

```python
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
```

- [ ] **Step 4: Run to confirm utility tests pass**

```powershell
pytest tests/test_core.py::TestBuildUrl tests/test_core.py::TestParseDateArg tests/test_core.py::TestFormatAmount -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add tally_xml_client/core.py tests/test_core.py
git commit -m "feat: add core utility functions with tests (build_url, parse_date_arg, format_amount)"
```

---

## Task 3: `core.py` — HTTP, XML, and public API (TDD)

**Files:**
- Modify: `tests/test_core.py` (add HTTP + XML tests)
- Modify: `tally_xml_client/core.py` (add HTTP, XML, public functions)

- [ ] **Step 1: Append HTTP and XML tests to `tests/test_core.py`**

Add the following classes after the existing ones:

```python
class TestParseVouchers:
    def test_filters_to_sales_only(self):
        xml = """<ENVELOPE>
          <VOUCHER>
            <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
            <DATE>20250401</DATE>
            <VOUCHERNUMBER>SAL/001</VOUCHERNUMBER>
            <PARTYLEDGERNAME>XYZ Traders</PARTYLEDGERNAME>
            <AMOUNT>-45000</AMOUNT>
          </VOUCHER>
          <VOUCHER>
            <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
            <DATE>20250401</DATE>
            <VOUCHERNUMBER>PUR/001</VOUCHERNUMBER>
            <AMOUNT>-5000</AMOUNT>
          </VOUCHER>
        </ENVELOPE>"""
        result = core.parse_vouchers(ET.fromstring(xml))
        assert len(result) == 1
        assert result[0]["voucher_no"] == "SAL/001"

    def test_amount_is_absolute_value(self):
        xml = """<ENVELOPE>
          <VOUCHER>
            <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
            <DATE>20250401</DATE>
            <VOUCHERNUMBER>SAL/001</VOUCHERNUMBER>
            <AMOUNT>-45000</AMOUNT>
          </VOUCHER>
        </ENVELOPE>"""
        result = core.parse_vouchers(ET.fromstring(xml))
        assert result[0]["amount"] == "45,000.00"

    def test_sorted_by_date_then_voucher_number(self):
        xml = """<ENVELOPE>
          <VOUCHER>
            <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
            <DATE>20250402</DATE>
            <VOUCHERNUMBER>SAL/002</VOUCHERNUMBER>
            <AMOUNT>-1000</AMOUNT>
          </VOUCHER>
          <VOUCHER>
            <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
            <DATE>20250401</DATE>
            <VOUCHERNUMBER>SAL/001</VOUCHERNUMBER>
            <AMOUNT>-2000</AMOUNT>
          </VOUCHER>
        </ENVELOPE>"""
        result = core.parse_vouchers(ET.fromstring(xml))
        assert result[0]["voucher_no"] == "SAL/001"
        assert result[1]["voucher_no"] == "SAL/002"

    def test_empty_envelope_returns_empty_list(self):
        root = ET.fromstring("<ENVELOPE></ENVELOPE>")
        assert core.parse_vouchers(root) == []


class TestPostXml:
    def test_connection_error_raises_runtime_error(self):
        with patch("tally_xml_client.core.requests.post") as mock_post:
            mock_post.side_effect = req_lib.exceptions.ConnectionError()
            with pytest.raises(RuntimeError, match="Cannot reach"):
                core._post_xml("<XML/>", "http://localhost:9000")

    def test_timeout_raises_runtime_error(self):
        with patch("tally_xml_client.core.requests.post") as mock_post:
            mock_post.side_effect = req_lib.exceptions.Timeout()
            with pytest.raises(RuntimeError, match="timed out"):
                core._post_xml("<XML/>", "http://localhost:9000")

    def test_invalid_xml_response_raises_runtime_error(self):
        mock_resp = MagicMock()
        mock_resp.content = b"not xml <<<>>>"
        mock_resp.raise_for_status = MagicMock()
        with patch("tally_xml_client.core.requests.post", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="parse"):
                core._post_xml("<XML/>", "http://localhost:9000")

    def test_valid_response_returns_element(self):
        mock_resp = MagicMock()
        mock_resp.content = b"<ROOT><DATA>ok</DATA></ROOT>"
        mock_resp.raise_for_status = MagicMock()
        with patch("tally_xml_client.core.requests.post", return_value=mock_resp):
            root = core._post_xml("<XML/>", "http://localhost:9000")
        assert root.tag == "ROOT"


class TestCheckConnection:
    def test_returns_company_name_from_name_element(self):
        mock_resp = MagicMock()
        mock_resp.content = (
            b"<ENVELOPE><COMPANY><NAME>ABC Pvt Ltd</NAME></COMPANY></ENVELOPE>"
        )
        mock_resp.raise_for_status = MagicMock()
        with patch("tally_xml_client.core.requests.post", return_value=mock_resp):
            name = core.check_connection("http://localhost:9000")
        assert name == "ABC Pvt Ltd"

    def test_propagates_runtime_error_on_connection_failure(self):
        with patch("tally_xml_client.core.requests.post") as mock_post:
            mock_post.side_effect = req_lib.exceptions.ConnectionError()
            with pytest.raises(RuntimeError):
                core.check_connection("http://localhost:9000")
```

- [ ] **Step 2: Run to confirm new tests fail**

```powershell
pytest tests/test_core.py::TestParseVouchers tests/test_core.py::TestPostXml tests/test_core.py::TestCheckConnection -v
```

Expected: `AttributeError` or `ImportError` — `parse_vouchers`, `_post_xml`, `check_connection` not yet defined.

- [ ] **Step 3: Append remaining functions to `tally_xml_client/core.py`**

Add after `_safe_text`:

```python
def _xml_company_info() -> str:
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


def _post_xml(xml_body: str, url: str) -> ET.Element:
    headers = {
        "Content-Type": "text/xml;charset=utf-8",
        "Content-Length": str(len(xml_body.encode("utf-8"))),
    }
    try:
        resp = requests.post(
            url, data=xml_body.encode("utf-8"), headers=headers, timeout=TALLY_TIMEOUT
        )
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Cannot reach TallyPrime at {url}. "
            "Ensure TallyPrime is running and the HTTP server is enabled on port 9000."
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(
            f"Request timed out after {TALLY_TIMEOUT}s. TallyPrime may be busy."
        )
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(f"HTTP error: {exc}")

    try:
        return ET.fromstring(resp.content)
    except ET.ParseError as exc:
        raise RuntimeError(f"Could not parse Tally response as XML: {exc}")


def parse_vouchers(root: ET.Element) -> list[dict]:
    vouchers = []
    for voucher in root.iter("VOUCHER"):
        vtype = (
            _safe_text(voucher.find("VOUCHERTYPENAME")) or voucher.get("VCHTYPE", "")
        ).strip()
        if vtype.lower() != "sales":
            continue
        row = {
            "date":       _parse_tally_date(_safe_text(voucher.find("DATE"))),
            "voucher_no": _safe_text(voucher.find("VOUCHERNUMBER")),
            "party":      _safe_text(voucher.find("PARTYLEDGERNAME")),
            "amount":     format_amount(_safe_text(voucher.find("AMOUNT"))),
            "narration":  _safe_text(voucher.find("NARRATION")),
            "reference":  _safe_text(voucher.find("REFERENCE")),
            "vch_type":   vtype,
        }
        vouchers.append(row)
    vouchers.sort(key=lambda v: (v["date"], v["voucher_no"]))
    return vouchers


def check_connection(url: str) -> str:
    root = _post_xml(_xml_company_info(), url)
    for company in root.iter("COMPANY"):
        name = company.findtext("NAME") or company.get("NAME", "")
        if name:
            return name
    return root.findtext(".//COMPANYNAME") or root.findtext(".//NAME") or "Unknown"


def fetch_vouchers(url: str, from_date: date, to_date: date) -> list[dict]:
    root = _post_xml(_xml_sales_vouchers(from_date, to_date), url)
    return parse_vouchers(root)
```

- [ ] **Step 4: Run the full test suite**

```powershell
pytest tests/test_core.py -v
```

Expected: `16 passed`

- [ ] **Step 5: Commit**

```bash
git add tally_xml_client/core.py tests/test_core.py
git commit -m "feat: complete core.py with HTTP, XML, and public API; all tests passing"
```

---

## Task 4: `cli.py` — migrate the CLI entry point

**Files:**
- Create: `tally_xml_client/cli.py`

- [ ] **Step 1: Create `tally_xml_client/cli.py`**

```python
import argparse
import sys
import textwrap
from datetime import date

from tally_xml_client import core

_COL_WIDTHS = {
    "date":       10,
    "voucher_no": 14,
    "party":      30,
    "amount":     14,
    "narration":  28,
    "reference":  14,
}
_HEADERS = {
    "date":       "Date",
    "voucher_no": "Voucher No.",
    "party":      "Party Name",
    "amount":     "Amount (₹)",
    "narration":  "Narration",
    "reference":  "Ref / Order No.",
}
_DISPLAY_COLS = ["date", "voucher_no", "party", "amount", "reference", "narration"]


def _cell(value: str, width: int, right_align: bool = False) -> str:
    truncated = value[: width - 1] + "…" if len(value) > width else value
    return truncated.rjust(width) if right_align else truncated.ljust(width)


def _print_vouchers(
    vouchers: list[dict], from_date: date, to_date: date, company: str
) -> None:
    sep = "  "
    cols = _DISPLAY_COLS
    header_line = sep.join(
        _cell(_HEADERS[c], _COL_WIDTHS[c], right_align=(c == "amount")) for c in cols
    )
    divider = sep.join("-" * _COL_WIDTHS[c] for c in cols)
    total_width = len(divider)
    title = (
        f"Sales Vouchers  |  {company}  |  "
        f"{from_date.strftime('%d-%m-%Y')} to {to_date.strftime('%d-%m-%Y')}"
    )
    print()
    print(title.center(total_width))
    print("=" * total_width)
    print(header_line)
    print(divider)

    grand_total = 0.0
    for v in vouchers:
        print(sep.join(
            _cell(v[c], _COL_WIDTHS[c], right_align=(c == "amount")) for c in cols
        ))
        try:
            grand_total += float(v["amount"].replace(",", ""))
        except ValueError:
            pass

    print(divider)
    total_label = f"Total  ({len(vouchers)} voucher{'s' if len(vouchers) != 1 else ''})"
    summary = []
    for c in cols:
        if c == "party":
            summary.append(_cell(total_label, _COL_WIDTHS[c]))
        elif c == "amount":
            summary.append(_cell(f"{grand_total:,.2f}", _COL_WIDTHS[c], right_align=True))
        else:
            summary.append(" " * _COL_WIDTHS[c])
    print(sep.join(summary))
    print()


def _prompt_date(prompt_text: str) -> date:
    while True:
        raw = input(prompt_text).strip()
        if not raw:
            continue
        try:
            return core.parse_date_arg(raw)
        except ValueError as exc:
            print(exc)


def _resolve_url(args: argparse.Namespace) -> str:
    if args.url:
        return args.url.rstrip("/")
    if not 1 <= args.port <= 65535:
        sys.exit(f"Invalid port: {args.port}. Must be between 1 and 65535.")
    return core.build_url(args.host, args.port)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tally_xml_client",
        description="List Sales Vouchers from a local TallyPrime Gold server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python main.py                                             # launches GUI
              python main.py -f 01-04-2025 -t 31-03-2026               # headless CLI
              python main.py -f 01-04-2025 -t 31-03-2026 --host 192.168.1.10
              python main.py -f 01-04-2025 -t 31-03-2026 --host 192.168.1.10 --port 9002
              python main.py -f 01-04-2025 -t 31-03-2026 --url http://tally.local:9000
        """),
    )
    p.add_argument("-f", "--from-date", metavar="DATE",
                   help="Start date  (DD-MM-YYYY | DD/MM/YYYY | YYYY-MM-DD)")
    p.add_argument("-t", "--to-date", metavar="DATE",
                   help="End date    (DD-MM-YYYY | DD/MM/YYYY | YYYY-MM-DD)")
    conn = p.add_argument_group(
        "server connection",
        "--url overrides --host / --port when provided.",
    )
    conn.add_argument("--host", default=core.TALLY_HOST, metavar="HOST",
                      help=f"TallyPrime server hostname or IP  (default: {core.TALLY_HOST})")
    conn.add_argument("--port", default=core.TALLY_PORT, metavar="PORT", type=int,
                      help=f"TallyPrime HTTP gateway port       (default: {core.TALLY_PORT})")
    conn.add_argument("--url", default=None, metavar="URL",
                      help="Full gateway URL — overrides --host and --port")
    p.add_argument("--no-narration", action="store_true",
                   help="Hide the Narration column")
    return p


def main() -> None:
    args = _build_parser().parse_args()

    try:
        from_date = (
            core.parse_date_arg(args.from_date)
            if args.from_date
            else _prompt_date("From date (DD-MM-YYYY): ")
        )
        to_date = (
            core.parse_date_arg(args.to_date)
            if args.to_date
            else _prompt_date("To   date (DD-MM-YYYY): ")
        )
    except ValueError as exc:
        sys.exit(str(exc))

    if from_date > to_date:
        sys.exit(f"from-date ({from_date}) must not be later than to-date ({to_date}).")

    url = _resolve_url(args)

    print(f"\nConnecting to TallyPrime at {url} …", end=" ", flush=True)
    try:
        company = core.check_connection(url)
    except RuntimeError as exc:
        sys.exit(str(exc))
    print(f"OK  [{company}]")

    print("Fetching Sales Vouchers …", end=" ", flush=True)
    try:
        vouchers = core.fetch_vouchers(url, from_date, to_date)
    except RuntimeError as exc:
        sys.exit(str(exc))
    print(f"found {len(vouchers)}.")

    if not vouchers:
        print(
            f"\nNo Sales Vouchers found between "
            f"{from_date.strftime('%d-%m-%Y')} and {to_date.strftime('%d-%m-%Y')}."
        )
        return

    if args.no_narration and "narration" in _DISPLAY_COLS:
        _DISPLAY_COLS.remove("narration")

    _print_vouchers(vouchers, from_date, to_date, company)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the module imports cleanly**

```powershell
python -c "from tally_xml_client.cli import main; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Run the full test suite to check nothing broke**

```powershell
pytest tests/ -v
```

Expected: `16 passed`

- [ ] **Step 4: Commit**

```bash
git add tally_xml_client/cli.py
git commit -m "feat: add cli.py — migrates CLI from tally_sales_vouchers.py"
```

---

## Task 5: `main.py` — unified entry point

**Files:**
- Create: `main.py`

- [ ] **Step 1: Create `main.py` at the repo root**

```python
#!/usr/bin/env python3
import sys

if len(sys.argv) > 1:
    from tally_xml_client.cli import main
    main()
else:
    from tally_xml_client.gui import launch
    launch()
```

- [ ] **Step 2: Verify CLI mode routes correctly**

```powershell
python main.py --help
```

Expected: prints the argparse help from `cli.py` (usage, -f, -t, --host, --port, --url).

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add main.py launcher (no args → GUI, args → CLI)"
```

---

## Task 6: `gui.py` — CustomTkinter window

**Files:**
- Create: `tally_xml_client/gui.py`

- [ ] **Step 1: Create `tally_xml_client/gui.py`**

```python
import json
import threading
from datetime import date
from pathlib import Path

import customtkinter as ctk

from tally_xml_client import core

_SETTINGS_FILE = Path.home() / ".tally_xml_client.json"

_COLS = ["date", "voucher_no", "party", "amount", "reference", "narration"]
_COL_LABELS = {
    "date":       "Date",
    "voucher_no": "Voucher No.",
    "party":      "Party Name",
    "amount":     "Amount (₹)",
    "reference":  "Ref / Order No.",
    "narration":  "Narration",
}
_COL_WIDTHS = {
    "date":       90,
    "voucher_no": 120,
    "party":      220,
    "amount":     110,
    "reference":  120,
    "narration":  200,
}
_RIGHT_ALIGN = {"amount"}


def _load_settings() -> dict:
    try:
        data = json.loads(_SETTINGS_FILE.read_text())
        return {
            "host": str(data.get("host", core.TALLY_HOST)),
            "port": int(data.get("port", core.TALLY_PORT)),
        }
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return {"host": core.TALLY_HOST, "port": core.TALLY_PORT}


def _save_settings(host: str, port: int) -> None:
    _SETTINGS_FILE.write_text(json.dumps({"host": host, "port": port}))


class TallyApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TallyPrime — Sales Vouchers")
        self.geometry("900x600")
        self.minsize(700, 450)
        self._settings = _load_settings()
        self._anim_job: str | None = None
        self._dot = 0
        self._row_widgets: list[list[ctk.CTkLabel]] = []
        self._build_ui()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Settings row
        sf = ctk.CTkFrame(self, corner_radius=0)
        sf.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(sf, text="SERVER", font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=0, column=0, padx=(12, 8), pady=8
        )
        ctk.CTkLabel(sf, text="Host").grid(row=0, column=1, padx=(0, 4))
        self._host_entry = ctk.CTkEntry(sf, width=160)
        self._host_entry.insert(0, self._settings["host"])
        self._host_entry.grid(row=0, column=2, padx=4)
        ctk.CTkLabel(sf, text="Port").grid(row=0, column=3, padx=(12, 4))
        self._port_entry = ctk.CTkEntry(sf, width=70)
        self._port_entry.insert(0, str(self._settings["port"]))
        self._port_entry.grid(row=0, column=4, padx=(4, 12))

        # Query row
        qf = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        qf.grid(row=1, column=0, sticky="ew", padx=12, pady=(8, 4))
        ctk.CTkLabel(qf, text="From").grid(row=0, column=0, padx=(0, 4))
        self._from_entry = ctk.CTkEntry(qf, width=110, placeholder_text="DD-MM-YYYY")
        self._from_entry.grid(row=0, column=1, padx=4)
        ctk.CTkLabel(qf, text="To").grid(row=0, column=2, padx=(12, 4))
        self._to_entry = ctk.CTkEntry(qf, width=110, placeholder_text="DD-MM-YYYY")
        self._to_entry.grid(row=0, column=3, padx=4)
        self._fetch_btn = ctk.CTkButton(qf, text="Fetch", width=90, command=self._on_fetch)
        self._fetch_btn.grid(row=0, column=4, padx=(16, 0))

        # Results table
        self._table_frame = ctk.CTkScrollableFrame(self)
        self._table_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
        for c_idx, col in enumerate(_COLS):
            self._table_frame.grid_columnconfigure(c_idx, minsize=_COL_WIDTHS[col])
            ctk.CTkLabel(
                self._table_frame,
                text=_COL_LABELS[col],
                font=ctk.CTkFont(weight="bold"),
                anchor="e" if col in _RIGHT_ALIGN else "w",
                width=_COL_WIDTHS[col],
            ).grid(row=0, column=c_idx, padx=4, pady=(4, 2), sticky="ew")

        # Totals row
        tf = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        tf.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 2))
        tf.grid_columnconfigure(0, weight=1)
        self._count_label = ctk.CTkLabel(tf, text="", anchor="w")
        self._count_label.grid(row=0, column=0, sticky="w")
        self._total_label = ctk.CTkLabel(tf, text="", anchor="e",
                                          font=ctk.CTkFont(weight="bold"))
        self._total_label.grid(row=0, column=1, sticky="e")
        self._totals_frame = tf
        self._totals_frame.grid_remove()

        # Status bar
        bar = ctk.CTkFrame(self, corner_radius=0, height=28)
        bar.grid(row=4, column=0, sticky="ew")
        bar.grid_propagate(False)
        self._status_label = ctk.CTkLabel(bar, text="● Ready", anchor="w",
                                           font=ctk.CTkFont(size=12))
        self._status_label.pack(side="left", padx=12)

    # ------------------------------------------------------------------
    # Fetch pipeline
    # ------------------------------------------------------------------

    def _on_fetch(self) -> None:
        host = self._host_entry.get().strip()
        port_str = self._port_entry.get().strip()
        from_str = self._from_entry.get().strip()
        to_str = self._to_entry.get().strip()

        if not host:
            self._set_status("Host cannot be empty", error=True)
            return
        try:
            port = int(port_str)
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            self._set_status("Port must be a number between 1 and 65535", error=True)
            return
        try:
            from_date = core.parse_date_arg(from_str)
        except ValueError:
            self._set_status("Invalid From date — use DD-MM-YYYY", error=True)
            return
        try:
            to_date = core.parse_date_arg(to_str)
        except ValueError:
            self._set_status("Invalid To date — use DD-MM-YYYY", error=True)
            return
        if from_date > to_date:
            self._set_status("From date must not be later than To date", error=True)
            return

        _save_settings(host, port)
        url = core.build_url(host, port)
        self._fetch_btn.configure(state="disabled")
        self._start_anim()
        threading.Thread(
            target=self._do_fetch, args=(url, from_date, to_date), daemon=True
        ).start()

    def _do_fetch(self, url: str, from_date: date, to_date: date) -> None:
        try:
            company = core.check_connection(url)
            vouchers = core.fetch_vouchers(url, from_date, to_date)
            self.after(0, lambda: self._on_success(company, vouchers))
        except RuntimeError as exc:
            msg = str(exc)
            self.after(0, lambda: self._on_error(msg))

    def _on_success(self, company: str, vouchers: list[dict]) -> None:
        self._stop_anim()
        self._fetch_btn.configure(state="normal")
        if not vouchers:
            self._set_status("● No Sales Vouchers found for the selected range")
            self._totals_frame.grid_remove()
            self._clear_table()
            return
        self._set_status(f"● Connected — {company}")
        self._redraw_table(vouchers)
        count = len(vouchers)
        total = 0.0
        for v in vouchers:
            try:
                total += float(v["amount"].replace(",", ""))
            except ValueError:
                pass
        self._count_label.configure(text=f"{count} voucher{'s' if count != 1 else ''}")
        self._total_label.configure(text=f"Total  ₹ {total:,.2f}")
        self._totals_frame.grid()

    def _on_error(self, message: str) -> None:
        self._stop_anim()
        self._fetch_btn.configure(state="normal")
        self._set_status(message, error=True)

    # ------------------------------------------------------------------
    # Table
    # ------------------------------------------------------------------

    def _clear_table(self) -> None:
        for row in self._row_widgets:
            for widget in row:
                widget.destroy()
        self._row_widgets.clear()

    def _redraw_table(self, vouchers: list[dict]) -> None:
        self._clear_table()
        for r_idx, v in enumerate(vouchers):
            bg = ("gray86", "gray20") if r_idx % 2 == 0 else ("gray90", "gray17")
            row: list[ctk.CTkLabel] = []
            for c_idx, col in enumerate(_COLS):
                lbl = ctk.CTkLabel(
                    self._table_frame,
                    text=v[col],
                    anchor="e" if col in _RIGHT_ALIGN else "w",
                    width=_COL_WIDTHS[col],
                    fg_color=bg,
                    corner_radius=0,
                )
                lbl.grid(row=r_idx + 1, column=c_idx, padx=2, pady=1, sticky="ew")
                row.append(lbl)
            self._row_widgets.append(row)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _set_status(self, text: str, error: bool = False) -> None:
        colour = "red" if error else ("gray10", "gray90")
        self._status_label.configure(text=text, text_color=colour)

    def _start_anim(self) -> None:
        self._dot = 0
        self._tick_anim()

    def _tick_anim(self) -> None:
        self._status_label.configure(text=f"Fetching{'.' * (self._dot % 4)}")
        self._dot += 1
        self._anim_job = self.after(400, self._tick_anim)

    def _stop_anim(self) -> None:
        if self._anim_job:
            self.after_cancel(self._anim_job)
            self._anim_job = None


def launch() -> None:
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    TallyApp().mainloop()
```

- [ ] **Step 2: Verify the module imports cleanly (no display required)**

```powershell
python -c "from tally_xml_client.gui import launch; print('OK')"
```

Expected: `OK` (no window opens; `launch` is not called)

- [ ] **Step 3: Run the full test suite**

```powershell
pytest tests/ -v
```

Expected: `16 passed`

- [ ] **Step 4: Commit**

```bash
git add tally_xml_client/gui.py
git commit -m "feat: add CustomTkinter GUI with settings persistence and background fetch"
```

---

## Task 7: Cleanup — delete old script, update README, push

**Files:**
- Delete: `tally_sales_vouchers.py`
- Modify: `README.md`

- [ ] **Step 1: Delete the old monolithic script**

```bash
git rm tally_sales_vouchers.py
```

- [ ] **Step 2: Rewrite `README.md`**

Replace the entire file with:

```markdown
# tally-xml-client

A Python tool that connects to a local **TallyPrime Gold** server and lists **Sales Vouchers** for any date range. Runs as a **desktop GUI** (default) or a **headless CLI** (when flags are passed).

Communication uses TallyPrime's built-in XML HTTP gateway with an inline TDL collection — no third-party Tally connector required.

---

## Requirements

| Requirement | Version |
|---|---|
| Python | 3.10 + |
| TallyPrime Gold | Any recent release |
| [`requests`](https://pypi.org/project/requests/) | Any |
| [`customtkinter`](https://pypi.org/project/customtkinter/) | Any |

```bash
pip install requests customtkinter
```

---

## TallyPrime setup (one-time)

1. Open TallyPrime and load your company.
2. Go to **Gateway of Tally → F12 (Configure) → Advanced Configuration**.
3. Set **"Enable TallyPrime to act as HTTP Server"** to **Yes**.
4. Leave the port at **9000** (default).

---

## Usage

### GUI (no arguments)

```bash
python main.py
```

Opens a desktop window. Enter the date range and click **Fetch**.

Server settings (host / port) are saved automatically to `~/.tally_xml_client.json` and restored on next launch.

### CLI (with arguments)

```bash
python main.py -f 01-04-2025 -t 31-03-2026
```

Runs headlessly and prints a formatted table to the terminal.

### All CLI options

```
options:
  -f, --from-date DATE   Start date
  -t, --to-date   DATE   End date
  --no-narration         Hide the Narration column

server connection:
  --host HOST            TallyPrime server hostname or IP  (default: localhost)
  --port PORT            TallyPrime HTTP gateway port       (default: 9000)
  --url  URL             Full gateway URL — overrides --host and --port
```

**Accepted date formats:** `DD-MM-YYYY` · `DD/MM/YYYY` · `YYYY-MM-DD` · `DD-Mon-YYYY`

### Connect to a remote server

```bash
python main.py -f 01-04-2025 -t 31-03-2026 --host 192.168.1.10
python main.py -f 01-04-2025 -t 31-03-2026 --host 192.168.1.10 --port 9002
python main.py -f 01-04-2025 -t 31-03-2026 --url http://tally.local:9000
```

---

## Project structure

```
tally-xml-client/
├── tally_xml_client/
│   ├── __init__.py   # package, version
│   ├── core.py       # HTTP, TDL XML, parsing — no side effects
│   ├── cli.py        # terminal UI and argparse
│   └── gui.py        # CustomTkinter desktop window
├── main.py           # entry point: no args → GUI, args → CLI
└── tests/
    └── test_core.py  # unit tests for core.py
```

---

## How it works

TallyPrime exposes an HTTP server accepting XML payloads in TDL schema. This tool POSTs an inline TDL collection request filtered to `VoucherTypeName = "Sales"` with date bounds applied server-side. No Tally SDK, COM object, or ODBC driver needed.
```

- [ ] **Step 3: Run tests one final time**

```powershell
pytest tests/ -v
```

Expected: `16 passed`

- [ ] **Step 4: Commit and push**

```bash
git add README.md
git commit -m "feat: complete GUI refactor — package structure, CustomTkinter GUI, updated docs"
git push origin master
```
```
