"""
Lab1 — Israel Housing Scraper GUI
===================================
Tkinter desktop application that drives the FastAPI backend at http://localhost:8001.

Layout:
  - Title bar:    API health indicator
  - Left column:  source selector, source-specific options, collect panel
  - Right column: records browser (filter bar, sortable table, pagination, detail popup)
"""

import json
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Optional

import requests

API_BASE = "http://localhost:8001"
PAGE_SIZE = 50

CBS_SERIES = [
    ("40010", "All Housing Prices (40010)"),
    ("70000", "New Construction (70000)"),
    ("140235", "Rent Index (140235)"),
]

ODATA_DEFAULT_RESOURCE = "5eb859da-6236-4b67-bcd1-ec4b90875739"

# (col_id, header_label, pixel_width, sortable_field)
TABLE_COLUMNS = [
    ("source",           "Source",          140, "source_name"),
    ("retrieval_method", "Method",           110, "retrieval_method"),
    ("ingested_at",      "Ingested At",      160, "ingested_at"),
    ("parsing_status",   "Status",            75, "parsing_status"),
    ("job_id",           "Job ID",           180, "job_id"),
    ("payload_preview",  "Payload Preview",  340, None),
]

SORT_ASC  = " ▲"
SORT_DESC = " ▼"


def _fmt_dt(val: str) -> str:
    if not val:
        return ""
    return val[:19].replace("T", " ")


def _payload_preview(payload: dict) -> str:
    if not isinstance(payload, dict):
        return str(payload)[:80]
    parts = [f"{k}={v}" for k, v in list(payload.items())[:4]]
    preview = "  |  ".join(parts)
    return preview[:120] + ("..." if len(preview) > 120 else "")


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Lab1 — Israel Housing Scraper")
        self.geometry("1280x780")
        self.minsize(900, 600)
        self.resizable(True, True)
        self.configure(bg="#f0f2f5")

        # Collect state
        self._current_job_id: Optional[str] = None
        self._poll_thread: Optional[threading.Thread] = None
        self._poll_stop = threading.Event()

        # Browser state
        self._current_page: int = 0
        self._total_records: int = 0
        self._sort_col: str = "ingested_at"
        self._sort_asc: bool = False
        self._all_items: list[dict] = []   # full page fetched, used for keyword filter

        self._build_ui()
        self._check_backend_health()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        title_frame = tk.Frame(self, bg="#2c3e50", pady=8)
        title_frame.pack(fill=tk.X)
        tk.Label(
            title_frame,
            text="Israel Housing Data Scraper — Lab 1",
            font=("Helvetica", 15, "bold"),
            fg="white",
            bg="#2c3e50",
        ).pack(side=tk.LEFT, padx=15)

        self._health_dot = tk.Label(
            title_frame, text="●", font=("Helvetica", 14), fg="#e74c3c", bg="#2c3e50"
        )
        self._health_dot.pack(side=tk.RIGHT, padx=10)
        tk.Label(title_frame, text="API", fg="#bdc3c7", bg="#2c3e50").pack(
            side=tk.RIGHT, padx=2
        )

        content = tk.Frame(self, bg="#f0f2f5")
        content.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)

        left = tk.Frame(content, bg="#f0f2f5", width=340)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left.pack_propagate(False)

        self._build_source_panel(left)
        self._build_options_panel(left)
        self._build_collect_panel(left)

        right = tk.Frame(content, bg="#f0f2f5")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_records_panel(right)

    # ── Left panels ─────────────────────────────────────────────────

    def _build_source_panel(self, parent: tk.Frame) -> None:
        card = self._card(parent, "Data Source")
        self._source_var = tk.StringVar(value="odata_il_nadlan")
        for value, label in [
            ("odata_il_nadlan", "odata.org.il — Real Estate (ZIP/XLSX)"),
            ("cbs_housing", "CBS — Housing Price Indices (REST API)"),
        ]:
            tk.Radiobutton(
                card,
                text=label,
                variable=self._source_var,
                value=value,
                bg="white", fg="black",
                selectcolor="white",
                activebackground="white", activeforeground="black",
                font=("Helvetica", 10),
                command=self._on_source_change,
            ).pack(anchor=tk.W, pady=2, padx=6)

    def _build_options_panel(self, parent: tk.Frame) -> None:
        self._options_frame = self._card(parent, "Source Options")

        self._odata_frame = tk.Frame(self._options_frame, bg="white")
        tk.Label(
            self._odata_frame, text="Resource ID:", bg="white", fg="black",
            font=("Helvetica", 9),
        ).grid(row=0, column=0, sticky=tk.W, padx=4, pady=3)
        self._odata_resource_var = tk.StringVar(value=ODATA_DEFAULT_RESOURCE)
        tk.Entry(
            self._odata_frame, textvariable=self._odata_resource_var, width=36,
            font=("Helvetica", 9), fg="black", bg="white", insertbackground="black",
        ).grid(row=0, column=1, padx=4, pady=3)
        self._odata_frame.pack(fill=tk.X, pady=2)

        self._cbs_frame = tk.Frame(self._options_frame, bg="white")
        tk.Label(
            self._cbs_frame, text="Series:", bg="white", fg="black",
            font=("Helvetica", 9, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=4, pady=(4, 1))

        self._cbs_series_vars: dict[str, tk.BooleanVar] = {}
        for i, (sid, label) in enumerate(CBS_SERIES):
            var = tk.BooleanVar(value=True)
            self._cbs_series_vars[sid] = var
            tk.Checkbutton(
                self._cbs_frame, text=label, variable=var,
                bg="white", fg="black",
                selectcolor="white",
                activebackground="white", activeforeground="black",
                font=("Helvetica", 9),
            ).grid(row=i + 1, column=0, columnspan=2, sticky=tk.W, padx=8, pady=1)

        tk.Label(
            self._cbs_frame, text="Start Period (MM-YYYY):", bg="white", fg="black",
            font=("Helvetica", 9),
        ).grid(row=len(CBS_SERIES) + 1, column=0, sticky=tk.W, padx=4, pady=4)
        self._cbs_start_var = tk.StringVar(value="")
        tk.Entry(
            self._cbs_frame, textvariable=self._cbs_start_var, width=12,
            font=("Helvetica", 9), fg="black", bg="white", insertbackground="black",
        ).grid(row=len(CBS_SERIES) + 1, column=1, sticky=tk.W, padx=4, pady=4)
        tk.Label(
            self._cbs_frame, text="(empty = full history)",
            bg="white", fg="#7f8c8d", font=("Helvetica", 8),
        ).grid(row=len(CBS_SERIES) + 2, column=0, columnspan=2, sticky=tk.W, padx=4)

        self._on_source_change()

    def _build_collect_panel(self, parent: tk.Frame) -> None:
        card = self._card(parent, "Collect")

        self._allow_dup_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            card,
            text="Allow duplicate records (bypass deduplication)",
            variable=self._allow_dup_var,
            bg="white", fg="#c0392b",
            selectcolor="white",
            activebackground="white", activeforeground="#c0392b",
            font=("Helvetica", 9),
        ).pack(anchor=tk.W, pady=(4, 6), padx=6)

        btn_frame = tk.Frame(card, bg="white")
        btn_frame.pack(fill=tk.X, padx=4, pady=(0, 6))

        self._collect_btn = tk.Button(
            btn_frame,
            text="▶  Collect",
            font=("Helvetica", 11, "bold"),
            bg="#27ae60", fg="black",
            activebackground="#2ecc71", activeforeground="black",
            highlightbackground="#27ae60",
            relief=tk.FLAT, padx=16, pady=6,
            cursor="hand2",
            command=self._on_collect,
        )
        self._collect_btn.pack(side=tk.LEFT)

        self._status_label = tk.Label(
            card, text="Status: idle",
            bg="white", font=("Helvetica", 9), fg="#333333",
            wraplength=290, justify=tk.LEFT,
        )
        self._status_label.pack(anchor=tk.W, padx=6, pady=4)

        self._progress_bar = ttk.Progressbar(card, mode="indeterminate", length=290)
        self._progress_bar.pack(padx=6, pady=(0, 6))

    # ── Right panel: records browser ─────────────────────────────────

    def _build_records_panel(self, parent: tk.Frame) -> None:
        outer = tk.Frame(parent, bg="#f0f2f5")
        outer.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            outer, text="RECORDS",
            font=("Helvetica", 8, "bold"), fg="#4a4a4a", bg="#f0f2f5",
        ).pack(anchor=tk.W, padx=2, pady=(0, 2))

        card = tk.Frame(outer, bg="white", relief=tk.RIDGE, bd=1)
        card.pack(fill=tk.BOTH, expand=True)

        self._build_filter_bar(card)
        self._build_tree(card)
        self._build_pagination_bar(card)

    def _build_filter_bar(self, parent: tk.Frame) -> None:
        bar = tk.Frame(parent, bg="white")
        bar.pack(fill=tk.X, padx=6, pady=(6, 2))

        # Row 1: source, status, keyword
        row1 = tk.Frame(bar, bg="white")
        row1.pack(fill=tk.X, pady=(0, 3))

        tk.Label(row1, text="Source:", bg="white", fg="black", font=("Helvetica", 9)).pack(side=tk.LEFT)
        self._filter_source_var = tk.StringVar(value="all")
        ttk.Combobox(
            row1, textvariable=self._filter_source_var,
            values=["all", "odata_il_nadlan", "cbs_housing"],
            state="readonly", width=16, font=("Helvetica", 9),
        ).pack(side=tk.LEFT, padx=(3, 10))

        tk.Label(row1, text="Status:", bg="white", fg="black", font=("Helvetica", 9)).pack(side=tk.LEFT)
        self._filter_status_var = tk.StringVar(value="all")
        ttk.Combobox(
            row1, textvariable=self._filter_status_var,
            values=["all", "raw", "parsed", "failed", "skipped"],
            state="readonly", width=10, font=("Helvetica", 9),
        ).pack(side=tk.LEFT, padx=(3, 10))

        tk.Label(row1, text="Keyword:", bg="white", fg="black", font=("Helvetica", 9)).pack(side=tk.LEFT)
        self._filter_keyword_var = tk.StringVar()
        kw_entry = tk.Entry(
            row1, textvariable=self._filter_keyword_var, width=18,
            font=("Helvetica", 9), fg="black", bg="white", insertbackground="black",
        )
        kw_entry.pack(side=tk.LEFT, padx=(3, 10))
        kw_entry.bind("<Return>", lambda _: self._apply_keyword_filter())
        self._filter_keyword_var.trace_add("write", lambda *_: self._apply_keyword_filter())

        # Row 2: dates, refresh, total
        row2 = tk.Frame(bar, bg="white")
        row2.pack(fill=tk.X, pady=(0, 3))

        tk.Label(row2, text="From:", bg="white", fg="black", font=("Helvetica", 9)).pack(side=tk.LEFT)
        self._filter_from_var = tk.StringVar()
        tk.Entry(
            row2, textvariable=self._filter_from_var, width=11,
            font=("Helvetica", 9), fg="black", bg="white", insertbackground="black",
        ).pack(side=tk.LEFT, padx=(3, 6))
        tk.Label(row2, text="To:", bg="white", fg="black", font=("Helvetica", 9)).pack(side=tk.LEFT)
        self._filter_to_var = tk.StringVar()
        tk.Entry(
            row2, textvariable=self._filter_to_var, width=11,
            font=("Helvetica", 9), fg="black", bg="white", insertbackground="black",
        ).pack(side=tk.LEFT, padx=(3, 10))
        tk.Label(row2, text="YYYY-MM-DD", bg="white", fg="#7f8c8d", font=("Helvetica", 8)).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            row2, text="⟳  Refresh",
            font=("Helvetica", 9), bg="#3498db", fg="black",
            activebackground="#2980b9", activeforeground="black",
            highlightbackground="#3498db",
            relief=tk.FLAT, padx=8, pady=3, cursor="hand2",
            command=self._on_refresh,
        ).pack(side=tk.LEFT)

        self._total_label = tk.Label(
            row2, text="Total: —", bg="white", font=("Helvetica", 9), fg="black",
        )
        self._total_label.pack(side=tk.RIGHT, padx=6)

    def _build_tree(self, parent: tk.Frame) -> None:
        tree_frame = tk.Frame(parent, bg="white")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(2, 0))

        cols = [c[0] for c in TABLE_COLUMNS]
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")

        for col_id, col_label, col_width, sort_field in TABLE_COLUMNS:
            display = col_label
            if sort_field and sort_field == self._sort_col:
                display += SORT_ASC if self._sort_asc else SORT_DESC
            if sort_field:
                self._tree.heading(col_id, text=display, command=lambda sf=sort_field: self._on_sort(sf))
            else:
                self._tree.heading(col_id, text=display)
            self._tree.column(col_id, width=col_width, minwidth=50, anchor=tk.W)

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self._tree.bind("<Double-1>", self._on_row_double_click)

    def _build_pagination_bar(self, parent: tk.Frame) -> None:
        bar = tk.Frame(parent, bg="white")
        bar.pack(fill=tk.X, padx=6, pady=4)

        self._prev_btn = tk.Button(
            bar, text="◀  Prev",
            font=("Helvetica", 9), bg="#ecf0f1", fg="black",
            activebackground="#bdc3c7", activeforeground="black",
            highlightbackground="#ecf0f1",
            relief=tk.FLAT, padx=8, pady=3, cursor="hand2",
            command=self._on_prev_page,
        )
        self._prev_btn.pack(side=tk.LEFT)

        self._page_label = tk.Label(
            bar, text="Page — of —",
            bg="white", fg="black", font=("Helvetica", 9),
        )
        self._page_label.pack(side=tk.LEFT, padx=10)

        self._next_btn = tk.Button(
            bar, text="Next  ▶",
            font=("Helvetica", 9), bg="#ecf0f1", fg="black",
            activebackground="#bdc3c7", activeforeground="black",
            highlightbackground="#ecf0f1",
            relief=tk.FLAT, padx=8, pady=3, cursor="hand2",
            command=self._on_next_page,
        )
        self._next_btn.pack(side=tk.LEFT)

        tk.Label(bar, text=f"({PAGE_SIZE}/page)", bg="white", fg="#7f8c8d", font=("Helvetica", 8)).pack(side=tk.LEFT, padx=6)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _card(self, parent: tk.Frame, title: str) -> tk.Frame:
        outer = tk.Frame(parent, bg="#f0f2f5")
        outer.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            outer, text=title.upper(),
            font=("Helvetica", 8, "bold"), fg="#4a4a4a", bg="#f0f2f5",
        ).pack(anchor=tk.W, padx=2, pady=(0, 2))
        inner = tk.Frame(outer, bg="white", relief=tk.RIDGE, bd=1)
        inner.pack(fill=tk.X)
        return inner

    def _on_source_change(self) -> None:
        src = self._source_var.get()
        if src == "odata_il_nadlan":
            self._cbs_frame.pack_forget()
            self._odata_frame.pack(fill=tk.X, pady=4, padx=4)
        else:
            self._odata_frame.pack_forget()
            self._cbs_frame.pack(fill=tk.X, pady=4, padx=4)

    def _set_status(self, msg: str, color: str = "#333333") -> None:
        self._status_label.config(text=f"Status: {msg}", fg=color)

    def _set_collecting(self, active: bool) -> None:
        if active:
            self._collect_btn.config(state=tk.DISABLED)
            self._progress_bar.start(12)
        else:
            self._collect_btn.config(state=tk.NORMAL)
            self._progress_bar.stop()

    def _update_sort_headers(self) -> None:
        for col_id, col_label, _, sort_field in TABLE_COLUMNS:
            display = col_label
            if sort_field and sort_field == self._sort_col:
                display += SORT_ASC if self._sort_asc else SORT_DESC
            self._tree.heading(col_id, text=display)
    def _update_pagination_controls(self) -> None:
        total_pages = max(1, -(-self._total_records // PAGE_SIZE))
        current = self._current_page + 1
        self._page_label.config(text=f"Page {current} of {total_pages}")
        self._prev_btn.config(state=tk.NORMAL if self._current_page > 0 else tk.DISABLED)
        self._next_btn.config(state=tk.NORMAL if current < total_pages else tk.DISABLED)

    # ------------------------------------------------------------------
    # Backend health check
    # ------------------------------------------------------------------

    def _check_backend_health(self) -> None:
        def _check() -> None:
            try:
                r = requests.get(f"{API_BASE}/health", timeout=3)
                ok = r.status_code == 200
            except Exception:
                ok = False
            self.after(0, lambda: self._health_dot.config(fg="#27ae60" if ok else "#e74c3c"))
            self.after(
                0,
                lambda: self._set_status(
                    "API online" if ok else "API offline — start Docker",
                    "#27ae60" if ok else "#e74c3c",
                ),
            )

        threading.Thread(target=_check, daemon=True).start()

    # ------------------------------------------------------------------
    # Collect
    # ------------------------------------------------------------------

    def _build_request_body(self) -> dict:
        src = self._source_var.get()
        body: dict[str, Any] = {"allow_duplicates": self._allow_dup_var.get()}

        if src == "cbs_housing":
            selected = [sid for sid, var in self._cbs_series_vars.items() if var.get()]
            if not selected:
                raise ValueError("Select at least one CBS series.")
            body["cbs_options"] = {
                "series_ids": ",".join(selected),
                "start_period": self._cbs_start_var.get().strip(),
            }
        else:
            resource_id = self._odata_resource_var.get().strip()
            if not resource_id:
                raise ValueError("Resource ID must not be empty.")
            body["odata_options"] = {"resource_id": resource_id}

        return body

    def _on_collect(self) -> None:
        try:
            body = self._build_request_body()
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
            return

        src = self._source_var.get()
        self._set_collecting(True)
        self._set_status("Submitting job...", "#e67e22")

        def _post() -> None:
            try:
                resp = requests.post(
                    f"{API_BASE}/api/collect/source/{src}",
                    json=body, timeout=10,
                )
                if resp.status_code == 202:
                    job_id = resp.json()["data"]["job_id"]
                    self.after(0, lambda: self._start_polling(job_id))
                elif resp.status_code == 409:
                    self.after(0, lambda: self._set_status("Job already running", "#e67e22"))
                    self.after(0, lambda: self._set_collecting(False))
                else:
                    msg = resp.text[:120]
                    self.after(0, lambda: self._set_status(f"Error {resp.status_code}: {msg}", "#e74c3c"))
                    self.after(0, lambda: self._set_collecting(False))
            except requests.ConnectionError:
                self.after(0, lambda: self._set_status("Cannot reach API — is Docker running?", "#e74c3c"))
                self.after(0, lambda: self._set_collecting(False))
            except Exception as exc:
                self.after(0, lambda: self._set_status(f"Request error: {exc}", "#e74c3c"))
                self.after(0, lambda: self._set_collecting(False))

        threading.Thread(target=_post, daemon=True).start()

    def _start_polling(self, job_id: str) -> None:
        self._current_job_id = job_id
        short_id = job_id[:8]
        self._set_status(f"Running… job {short_id}…", "#e67e22")

        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_stop.set()
        self._poll_stop.clear()
        self._poll_thread = threading.Thread(
            target=self._poll_job, args=(job_id,), daemon=True
        )
        self._poll_thread.start()

    def _poll_job(self, job_id: str) -> None:
        short_id = job_id[:8]
        while not self._poll_stop.is_set():
            try:
                resp = requests.get(f"{API_BASE}/api/jobs/{job_id}", timeout=5)
                if resp.status_code != 200:
                    break
                job = resp.json()["data"]
                status = job.get("status", "")
                inserted = job.get("records_inserted", 0)
                skipped = job.get("records_skipped", 0)

                if status == "running":
                    msg = f"Running… {inserted} inserted, {skipped} skipped (job {short_id})"
                    self.after(0, lambda m=msg: self._set_status(m, "#e67e22"))
                elif status == "completed":
                    msg = f"Completed — {inserted} inserted, {skipped} skipped"
                    self.after(0, lambda m=msg: self._set_status(m, "#27ae60"))
                    self.after(0, lambda: self._set_collecting(False))
                    self.after(500, self._on_refresh)
                    break
                elif status == "failed":
                    err = (job.get("error_message") or "unknown error")[:80]
                    self.after(0, lambda e=err: self._set_status(f"Failed: {e}", "#e74c3c"))
                    self.after(0, lambda: self._set_collecting(False))
                    break
                elif status == "partial":
                    self.after(0, lambda: self._set_status("Partial completion", "#e67e22"))
                    self.after(0, lambda: self._set_collecting(False))
                    self.after(500, self._on_refresh)
                    break

            except Exception:
                pass

            time.sleep(2)

    # ------------------------------------------------------------------
    # Browser — sort
    # ------------------------------------------------------------------

    def _on_sort(self, sort_field: str) -> None:
        if self._sort_col == sort_field:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = sort_field
            self._sort_asc = True
        self._current_page = 0
        self._update_sort_headers()
        self._on_refresh()

    # ------------------------------------------------------------------
    # Browser — pagination
    # ------------------------------------------------------------------

    def _on_prev_page(self) -> None:
        if self._current_page > 0:
            self._current_page -= 1
            self._on_refresh()

    def _on_next_page(self) -> None:
        total_pages = max(1, -(-self._total_records // PAGE_SIZE))
        if self._current_page + 1 < total_pages:
            self._current_page += 1
            self._on_refresh()

    # ------------------------------------------------------------------
    # Browser — fetch & display
    # ------------------------------------------------------------------

    def _on_refresh(self) -> None:
        src_filter  = self._filter_source_var.get()
        stat_filter = self._filter_status_var.get()
        date_from   = self._filter_from_var.get().strip()
        date_to     = self._filter_to_var.get().strip()

        params: dict[str, Any] = {
            "limit":      PAGE_SIZE,
            "offset":     self._current_page * PAGE_SIZE,
            "sort_by":    self._sort_col,
            "sort_order": 1 if self._sort_asc else -1,
        }
        if src_filter != "all":
            params["source_name"] = src_filter
        if stat_filter != "all":
            params["parsing_status"] = stat_filter
        if date_from:
            params["ingested_after"] = date_from + "T00:00:00"
        if date_to:
            params["ingested_before"] = date_to + "T23:59:59"

        def _fetch() -> None:
            try:
                resp = requests.get(f"{API_BASE}/api/records", params=params, timeout=10)
                if resp.status_code != 200:
                    return
                data = resp.json().get("data", {})
                items = data.get("items", [])
                total = data.get("total", 0)
                self.after(0, lambda: self._populate_table(items, total))
            except Exception as exc:
                self.after(0, lambda e=exc: self._set_status(f"Refresh error: {e}", "#e74c3c"))

        threading.Thread(target=_fetch, daemon=True).start()

    def _populate_table(self, items: list[dict], total: int) -> None:
        self._all_items = items
        self._total_records = total
        self._total_label.config(text=f"Total: {total:,}")
        self._update_pagination_controls()
        self._apply_keyword_filter()

    def _apply_keyword_filter(self) -> None:
        keyword = self._filter_keyword_var.get().strip().lower()
        self._tree.delete(*self._tree.get_children())

        for rec in self._all_items:
            payload = rec.get("raw_payload", {})
            preview = _payload_preview(payload)

            if keyword and keyword not in preview.lower() and keyword not in rec.get("source_name", "").lower():
                continue

            row = (
                rec.get("source_name", ""),
                rec.get("retrieval_method", ""),
                _fmt_dt(rec.get("ingested_at", "")),
                rec.get("parsing_status", ""),
                (rec.get("job_id") or "")[:24],
                preview,
            )
            record_id = str(rec.get("id") or rec.get("_id") or "")
            self._tree.insert("", tk.END, iid=record_id or None, values=row)

    # ------------------------------------------------------------------
    # Browser — record detail popup
    # ------------------------------------------------------------------

    def _on_row_double_click(self, event: tk.Event) -> None:
        item = self._tree.focus()
        if not item:
            return
        threading.Thread(
            target=self._fetch_and_show_detail, args=(item,), daemon=True
        ).start()

    def _fetch_and_show_detail(self, record_id: str) -> None:
        try:
            resp = requests.get(f"{API_BASE}/api/records/{record_id}", timeout=8)
            if resp.status_code != 200:
                self.after(0, lambda: messagebox.showerror("Error", f"Could not load record: {resp.status_code}"))
                return
            rec = resp.json().get("data", {})
            self.after(0, lambda: self._show_detail_window(rec))
        except Exception as exc:
            self.after(0, lambda e=exc: messagebox.showerror("Error", str(e)))

    def _show_detail_window(self, rec: dict) -> None:
        win = tk.Toplevel(self)
        win.title(f"Record — {rec.get('source_name', '')}  {_fmt_dt(rec.get('ingested_at', ''))}")
        win.geometry("900x600")
        win.resizable(True, True)
        win.configure(bg="#f0f2f5")

        paned = tk.PanedWindow(win, orient=tk.HORIZONTAL, bg="#f0f2f5", sashwidth=6)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # ── Left: metadata ──
        meta_frame = tk.Frame(paned, bg="white", relief=tk.RIDGE, bd=1)
        paned.add(meta_frame, minsize=250)

        tk.Label(
            meta_frame, text="METADATA",
            font=("Helvetica", 8, "bold"), fg="#4a4a4a", bg="white",
        ).pack(anchor=tk.W, padx=8, pady=(8, 4))

        meta_fields = [
            ("ID",             str(rec.get("id") or rec.get("_id") or "")),
            ("Source",         rec.get("source_name", "")),
            ("Method",         rec.get("retrieval_method", "")),
            ("Ingested At",    _fmt_dt(rec.get("ingested_at", ""))),
            ("Status",         rec.get("parsing_status", "")),
            ("Schema",         rec.get("schema_version", "")),
            ("Job ID",         str(rec.get("job_id") or "")),
            ("Content Hash",   (rec.get("content_hash") or "")[:24] + "…"),
            ("Source URL",     rec.get("source_url", "")),
        ]

        for label, value in meta_fields:
            row = tk.Frame(meta_frame, bg="white")
            row.pack(fill=tk.X, padx=8, pady=2)
            tk.Label(
                row, text=f"{label}:", bg="white", fg="#555555",
                font=("Helvetica", 9, "bold"), width=12, anchor=tk.W,
            ).pack(side=tk.LEFT)
            tk.Label(
                row, text=value, bg="white", fg="black",
                font=("Helvetica", 9), anchor=tk.W, wraplength=180, justify=tk.LEFT,
            ).pack(side=tk.LEFT)

        tags = rec.get("tags") or []
        if tags:
            row = tk.Frame(meta_frame, bg="white")
            row.pack(fill=tk.X, padx=8, pady=2)
            tk.Label(row, text="Tags:", bg="white", fg="#555555", font=("Helvetica", 9, "bold"), width=12, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, text=", ".join(tags), bg="white", fg="black", font=("Helvetica", 9), anchor=tk.W).pack(side=tk.LEFT)

        # ── Right: raw_payload JSON ──
        json_frame = tk.Frame(paned, bg="white", relief=tk.RIDGE, bd=1)
        paned.add(json_frame, minsize=400)

        tk.Label(
            json_frame, text="RAW PAYLOAD",
            font=("Helvetica", 8, "bold"), fg="#4a4a4a", bg="white",
        ).pack(anchor=tk.W, padx=8, pady=(8, 4))

        text_area = tk.Text(
            json_frame,
            font=("Courier", 10),
            fg="black", bg="#fafafa",
            wrap=tk.NONE,
            relief=tk.FLAT,
            state=tk.NORMAL,
        )
        vsb = ttk.Scrollbar(json_frame, orient=tk.VERTICAL, command=text_area.yview)
        hsb = ttk.Scrollbar(json_frame, orient=tk.HORIZONTAL, command=text_area.xview)
        text_area.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        text_area.pack(fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 8))

        payload = rec.get("raw_payload", {})
        text_area.insert(tk.END, json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        text_area.config(state=tk.DISABLED)

        tk.Button(
            win, text="Close",
            font=("Helvetica", 9), bg="#ecf0f1", fg="black",
            activebackground="#bdc3c7", activeforeground="black",
            highlightbackground="#ecf0f1",
            relief=tk.FLAT, padx=12, pady=4,
            command=win.destroy,
        ).pack(pady=(0, 8))


if __name__ == "__main__":
    app = App()
    app.mainloop()
