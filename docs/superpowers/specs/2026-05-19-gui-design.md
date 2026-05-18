# GUI Design Spec — tally-xml-client
Date: 2026-05-19

## Overview

Add a CustomTkinter GUI to the existing TallyPrime Sales Voucher CLI tool. The GUI coexists with the CLI: running `main.py` with no arguments launches the window; passing `-f`/`-t` flags runs headlessly as before.

---

## Architecture

Restructure the repo from a single script into a Python package:

```
tally-xml-client/
├── tally_xml_client/
│   ├── __init__.py       # package marker, exposes __version__
│   ├── core.py           # HTTP requests, TDL XML builders, parsing, date utils
│   ├── cli.py            # argparse entry point — imports core, runs headless
│   └── gui.py            # CustomTkinter window — imports core, persists settings
├── main.py               # launcher: no args → GUI, args present → CLI
├── README.md
└── docs/
```

`tally_sales_vouchers.py` is deleted; its logic is distributed into `core.py` and `cli.py`.

`core.py` is pure logic — no argparse, no tkinter, no I/O side effects. Both `cli.py` and `gui.py` are consumers of it.

---

## Package Modules

### `core.py`
Extracted and reorganised from the existing script. Public API:

| Function | Signature | Description |
|---|---|---|
| `check_connection` | `(url: str) -> str` | Returns active company name or raises |
| `fetch_vouchers` | `(url: str, from_date: date, to_date: date) -> list[dict]` | Full pipeline: build request → POST → parse → return rows |
| `build_url` | `(host: str, port: int) -> str` | Constructs `http://host:port` |
| `parse_date_arg` | `(s: str) -> date` | Accepts DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD, DD-Mon-YYYY |
| `format_amount` | `(raw: str) -> str` | Absolute value, comma-formatted |

Raises plain `RuntimeError` with a human-readable message on connectivity / parse failures (no `sys.exit` — callers decide how to surface errors).

### `cli.py`
Thin wrapper. Imports `core`, calls `fetch_vouchers`, prints the table. Mirrors the current `main()` behaviour exactly. Entry point: `python -m tally_xml_client.cli` or via `main.py`.

### `gui.py`
CustomTkinter application class `TallyApp(ctk.CTk)`. Described in the GUI Layout section below.

### `main.py`
```python
if len(sys.argv) > 1:
    from tally_xml_client.cli import main; main()
else:
    from tally_xml_client.gui import launch; launch()
```

---

## Settings Persistence

File: `~/.tally_xml_client.json`

```json
{ "host": "localhost", "port": 9000 }
```

- Loaded on app start; missing file → defaults.
- Written on every Fetch (only if values changed).
- CLI ignores this file; it uses its own `--host`/`--port`/`--url` flags.

---

## GUI Layout

Single window, fixed initial size (860 × 580 px), resizable vertically.

```
┌─────────────────────────────────────────────────┐
│  SERVER          Host [localhost    ] Port [9000]│  settings row
├─────────────────────────────────────────────────┤
│  From [01-04-2025]  To [31-03-2026]   [Fetch]   │  query row
├─────────────────────────────────────────────────┤
│  Date      Voucher No.  Party        Amount      │
│  ─────────────────────────────────────────────   │
│  01-04-25  SAL/001      XYZ Traders  45,000.00   │  results table
│  ...                                             │  (scrollable)
│  ─────────────────────────────────────────────   │
│  42 vouchers                      8,34,250.00    │  totals row
├─────────────────────────────────────────────────┤
│  ● Connected — ABC Pvt Ltd                       │  status bar
└─────────────────────────────────────────────────┘
```

**Settings row** — `CTkEntry` fields for host and port, pre-filled from persisted config.

**Query row** — two `CTkEntry` date fields (DD-MM-YYYY placeholder text) and a `CTkButton`. Button disables during fetch to prevent double-submission.

**Results table** — `CTkScrollableFrame` with a label grid. Columns: Date, Voucher No., Party Name, Amount (₹), Ref / Order No., Narration. Amount column right-aligned.

**Totals row** — voucher count (left) and grand total (right). Hidden until first successful fetch.

**Status bar** — single label row at the bottom:
- Idle: `● Ready`
- Fetching: animated `… Fetching` (cycles dots via `after()`)
- Success: `● Connected — <Company Name>`
- Error: `✕ <error message>` (red text)
- No results: `● No Sales Vouchers found for the selected range`

---

## Data Flow

1. User clicks **Fetch**.
2. UI thread: validates host (non-empty), port (1–65535), from/to dates (parseable, from ≤ to). Shows inline error in status bar on failure — no modal dialogs.
3. UI thread: persists host/port to `~/.tally_xml_client.json`, disables Fetch button, starts status animation.
4. Background thread (`threading.Thread`): calls `core.check_connection(url)` then `core.fetch_vouchers(url, from_date, to_date)`.
5. Background thread posts result back with `widget.after(0, callback)`.
6. UI thread: re-enables Fetch, stops animation, redraws table and totals (or shows error in status bar).

---

## Error Handling

All errors are shown in the status bar. No modal popups.

| Error | Message shown |
|---|---|
| Empty host | `Host cannot be empty` |
| Invalid port | `Port must be a number between 1 and 65535` |
| Invalid date format | `Invalid date: use DD-MM-YYYY` |
| from > to | `From date must not be later than To date` |
| Connection refused | `Cannot reach TallyPrime at <url> — is it running?` |
| Timeout | `Request timed out — TallyPrime may be busy` |
| XML parse failure | `Unexpected response from TallyPrime` |
| No vouchers | `No Sales Vouchers found for the selected range` (neutral colour) |

---

## Dependencies

```
customtkinter   # pip install customtkinter
requests        # already a dependency
```

Python ≥ 3.10 (already required by type hint syntax in existing code).

---

## Out of Scope

- Export to CSV / Excel (deferred)
- Voucher detail drill-down
- Multiple company support
- Dark / light theme toggle (CustomTkinter defaults to system theme)
