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
