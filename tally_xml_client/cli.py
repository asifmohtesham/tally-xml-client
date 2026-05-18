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
