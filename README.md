# tally-xml-client

A Python CLI that connects to a local **TallyPrime Gold** server and lists **Sales Vouchers** for any date range — directly from your terminal, no third-party Tally connector required.

Communication happens over TallyPrime's built-in **XML HTTP gateway** using an inline TDL collection, so filtering is done server-side and only matching vouchers are returned.

---

## Requirements

| Requirement | Version |
|---|---|
| Python | 3.10 + |
| TallyPrime Gold | Any recent release |
| [`requests`](https://pypi.org/project/requests/) | Any |

Install the dependency:

```bash
pip install requests
```

---

## TallyPrime setup (one-time)

The XML gateway must be enabled in TallyPrime before running this tool:

1. Open TallyPrime and load your company.
2. Go to **Gateway of Tally → F12 (Configure) → Advanced Configuration**.
3. Set **"Enable TallyPrime to act as HTTP Server"** to **Yes**.
4. Note the port — **9000** is the default and what this tool uses.

---

## Usage

### Interactive mode (prompts for dates)

```bash
python tally_sales_vouchers.py
```

```
From date (DD-MM-YYYY): 01-04-2025
To   date (DD-MM-YYYY): 31-03-2026

Connecting to TallyPrime at http://localhost:9000 … OK  [ABC Pvt Ltd]
Fetching Sales Vouchers … found 42.
```

### CLI flags

```bash
python tally_sales_vouchers.py -f 01-04-2025 -t 31-03-2026
```

### All options

```
usage: tally_sales_vouchers [-h] [-f DATE] [-t DATE] [--host HOST] [--port PORT] [--url URL] [--no-narration]

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

### Connect to a remote or non-default server

```bash
# Different host (LAN machine running TallyPrime)
python tally_sales_vouchers.py -f 01-04-2025 -t 31-03-2026 --host 192.168.1.10

# Different host and port
python tally_sales_vouchers.py -f 01-04-2025 -t 31-03-2026 --host 192.168.1.10 --port 9002

# Full URL override (e.g. named host, non-standard scheme)
python tally_sales_vouchers.py -f 01-04-2025 -t 31-03-2026 --url http://tally.local:9000
```

`--url` takes precedence when provided alongside `--host`/`--port`.

---

## Sample output

```
          Sales Vouchers  |  ABC Pvt Ltd  |  01-04-2025 to 31-03-2026
================================================================================
Date        Voucher No.     Party Name                     Amount (Rs)   Ref / Order No.   Narration
----------  --------------  -----------------------------  ------------  ----------------  ----------------------------
01-04-2025  SAL/25-26/001   XYZ Traders                      45,000.00  PO-2025-001        GST Invoice
03-04-2025  SAL/25-26/002   Ravi Enterprises                1,12,500.00  PO-2025-002        Monthly supply
...
----------  --------------  -----------------------------  ------------  ----------------  ----------------------------
                            Total  (42 vouchers)           8,34,250.00
```

Columns displayed: Date · Voucher No. · Party Name · Amount · Ref / Order No. · Narration

---

## How it works

TallyPrime exposes an HTTP server that accepts XML payloads following the **TDL (Tally Definition Language)** schema. This tool:

1. **Checks connectivity** by querying the active company name.
2. **Sends a TDL collection request** with `VoucherTypeName = "Sales"` and the requested date bounds (`SVFROMDATE` / `SVTODATE`) applied server-side.
3. **Parses the XML response** and renders results as a formatted table with a grand total.

No Tally SDK, COM object, or ODBC driver is needed — just a plain HTTP POST.

---

## Files

| File | Description |
|---|---|
| `tally_sales_vouchers.py` | Main script — self-contained, single file |
