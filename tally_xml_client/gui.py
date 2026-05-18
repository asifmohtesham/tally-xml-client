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
        self._total_label = ctk.CTkLabel(
            tf, text="", anchor="e", font=ctk.CTkFont(weight="bold")
        )
        self._total_label.grid(row=0, column=1, sticky="e")
        self._totals_frame = tf
        self._totals_frame.grid_remove()

        # Status bar
        bar = ctk.CTkFrame(self, corner_radius=0, height=28)
        bar.grid(row=4, column=0, sticky="ew")
        bar.grid_propagate(False)
        self._status_label = ctk.CTkLabel(
            bar, text="● Ready", anchor="w", font=ctk.CTkFont(size=12)
        )
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
