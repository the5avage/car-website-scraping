import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import json
import copy

"""
GUI query manager – two‑column version (Queries | Car brand)
===========================================================

Shortcuts & Controls
--------------------
• **Enter / Add**   – add a new row (Query required, Brand optional)
• **Click a cell**  – pick column for autofill (only when entry box empty)
• **Update**        – overwrite the selected row with the contents of the entry boxes
• **Delete / Del**  – remove highlighted rows (multi‑select with Ctrl / Shift)
• **Undo / Redo**   – Ctrl+Z / Ctrl+Y
• **Finish**        – save & exit
• **Cancel**        – exit without saving

The list is persisted as a JSON array of objects with keys ``query`` and ``brand``.
"""

# --------------------------------------------------------------------
#  Persistence helpers
# --------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent / "data"  # project‑level data dir
QUERIES_FILE = DATA_DIR / "queries.json"


def load_queries() -> list[dict]:
    """Load saved rows or return an empty list."""
    try:
        raw = json.loads(QUERIES_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return [
                {"query": str(item.get("query", "")), "brand": str(item.get("brand", ""))}
                for item in raw if isinstance(item, dict)
            ]
    except FileNotFoundError:
        return []
    except (json.JSONDecodeError, UnicodeDecodeError):
        messagebox.showerror("Error", "queries.json is corrupted – starting fresh.")
    return []


def save_queries(rows: list[dict]):
    DATA_DIR.mkdir(exist_ok=True)
    QUERIES_FILE.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


# --------------------------------------------------------------------
#  Main GUI class
# --------------------------------------------------------------------


class QueryGUI(tk.Tk):
    HELP_TEXT = (
        "Controls:\n\n"
        "• Add / Enter  – add a row.\n"
        "• Click a cell – select column for autofill.\n"
        "• Update       – overwrite the selected row.\n"
        "• Delete / Del – remove highlighted rows.\n"
        "• Undo / Redo  – Ctrl+Z / Ctrl+Y.\n"
        "• Finish       – save & exit.\n"
        "• Cancel       – exit without saving."
    )

    def __init__(self):
        super().__init__()
        self.title("Car‑Alert Query Manager")
        self.geometry("660x560")
        self.resizable(False, False)

        # -------- Data -------- #
        self.rows: list[dict] = load_queries()
        self.undo_stack: list[list[dict]] = []
        self.redo_stack: list[list[dict]] = []
        self.selected_column: int | None = None  # 0 = query, 1 = brand

        # -------- UI -------- #
        self._build_menu()
        self._build_widgets()
        self.refresh_tree()

        # Global key‑bindings
        self.bind_all("<Control-z>", self.undo)
        self.bind_all("<Control-y>", self.redo)
        self.bind_all("<Delete>", lambda _e: self.delete_selected())

    # -------------------- Menu -------------------- #
    def _build_menu(self):
        menubar = tk.Menu(self)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Controls", command=self.show_help)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)

    def show_help(self):
        messagebox.showinfo("Help – Controls", self.HELP_TEXT)

    # -------------------- Widgets -------------------- #
    def _build_widgets(self):
        # Treeview frame
        tv_frame = tk.Frame(self)
        tv_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("query", "brand")
        self.tree = ttk.Treeview(
            tv_frame,
            columns=cols,
            show="headings",
            selectmode="extended",
            height=17,
        )
        self.tree.heading("query", text="Queries")
        self.tree.heading("brand", text="Car brand")
        self.tree.column("query", width=320)
        self.tree.column("brand", width=200)

        tv_scroll = tk.Scrollbar(tv_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tv_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tv_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<ButtonRelease-1>", self.on_click)

        # --- Entry fields --- #
        form = tk.Frame(self)
        form.pack(fill=tk.X, padx=10)

        tk.Label(form, text="Query:").grid(row=0, column=0, sticky="w")
        self.entry_query = tk.Entry(form)
        self.entry_query.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        form.columnconfigure(1, weight=1)

        tk.Label(form, text="Car brand:").grid(row=0, column=2, sticky="w")
        self.entry_brand = tk.Entry(form, width=18)
        self.entry_brand.grid(row=0, column=3, sticky="w")

        # Bind Enter in either entry to add
        self.entry_query.bind("<Return>", self.add_row)
        self.entry_brand.bind("<Return>", self.add_row)

        # --- Action buttons --- #
        btn_row = tk.Frame(self)
        btn_row.pack(fill=tk.X, padx=10, pady=8)

        tk.Button(btn_row, text="Add", width=10, command=self.add_row).pack(side=tk.LEFT)
        tk.Button(btn_row, text="Update", width=10, command=self.update_row).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row, text="Delete selected", command=self.delete_selected).pack(side=tk.LEFT, padx=5)

        # --- Finish / Cancel bottom‑right --- #
        bottom = tk.Frame(self)
        bottom.pack(fill=tk.X, padx=10, pady=(0, 10), anchor="e")

        tk.Button(bottom, text="Finish", width=10, command=self.finish_and_exit).pack(side=tk.RIGHT, padx=5)
        tk.Button(bottom, text="Cancel", width=10, command=self.quit_without_save).pack(side=tk.RIGHT, padx=5)

    # -------------------- Utils -------------------- #
    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for idx, row in enumerate(self.rows):
            self.tree.insert("", tk.END, iid=str(idx), values=(row["query"], row["brand"]))

    def clear_entries(self):
        self.entry_query.delete(0, tk.END)
        self.entry_brand.delete(0, tk.END)

    # -------------------- Undo/Redo -------------------- #
    def push_undo(self):
        self.undo_stack.append(copy.deepcopy(self.rows))
        self.redo_stack.clear()

    def undo(self, _evt=None):
        if not self.undo_stack:
            return
        self.redo_stack.append(copy.deepcopy(self.rows))
        self.rows = self.undo_stack.pop()
        self.refresh_tree()
        self.clear_entries()

    def redo(self, _evt=None):
        if not self.redo_stack:
            return
        self.undo_stack.append(copy.deepcopy(self.rows))
        self.rows = self.redo_stack.pop()
        self.refresh_tree()
        self.clear_entries()

    # -------------------- Event Handlers -------------------- #
    def on_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        self.selected_column = None if region != "cell" else int(self.tree.identify_column(event.x).lstrip("#")) - 1

    def on_select(self, _evt=None):
        sel = self.tree.selection()
        if len(sel) != 1:
            return
        idx = int(sel[0])
        row = self.rows[idx]

        # Auto‑fill corresponding entry only if empty
        if self.selected_column == 0 and not self.entry_query.get().strip():
            self.entry_query.insert(0, row["query"])
        elif self.selected_column == 1 and not self.entry_brand.get().strip():
            self.entry_brand.insert(0, row["brand"])
        elif self.selected_column is None and not self.entry_query.get().strip() and not self.entry_brand.get().strip():
            self.entry_query.insert(0, row["query"])
            self.entry_brand.insert(0, row["brand"])

    # -------------------- CRUD -------------------- #
    def add_row(self, _evt=None):
        q = self.entry_query.get().strip()
        b = self.entry_brand.get().strip()
        if not q:
            return  # Query is mandatory
        if any(r["query"] == q and r["brand"] == b for r in self.rows):
            messagebox.showinfo("Info", "Entry already exists.")
            return
        self.push_undo()
        self.rows.append({"query": q, "brand": b})
        self.refresh_tree()
        self.tree.see(str(len(self.rows) - 1))
        self.clear_entries()
        self.selected_column = None

    def update_row(self):
        sel = self.tree.selection()
        if len(sel) != 1:
            messagebox.showinfo("Info", "Select exactly one row to update.")
            return
        idx = int(sel[0])
        row = self.rows[idx]

        # Determine new values – if entry box empty keep existing value
        new_q = self.entry_query.get().strip() or row["query"]
        new_b = self.entry_brand.get().strip() or row["brand"]

        # Prevent duplicates except for the row being edited
        if any(i != idx and r["query"] == new_q and r["brand"] == new_b for i, r in enumerate(self.rows)):
            messagebox.showinfo("Info", "Another identical row already exists.")
            return

        self.push_undo()
        self.rows[idx] = {"query": new_q, "brand": new_b}
        self.refresh_tree()
        self.tree.selection_set(str(idx))
        self.clear_entries()
        self.selected_column = None

    def delete_selected(self):
        sels = [int(i) for i in self.tree.selection()]
        if not sels:
            return
        self.push_undo()
        for idx in sorted(sels, reverse=True):
            self.rows.pop(idx)
        self.refresh_tree()
        self.clear_entries()
        self.selected_column = None

    # -------------------- Exit helpers -------------------- #
    def quit_without_save(self):
        self.destroy()

    def finish_and_exit(self):
        save_queries(self.rows)
        self.destroy()


# --------------------------------------------------------------------
#  Run standalone
# --------------------------------------------------------------------

if __name__ == "__main__":
    QueryGUI().mainloop()
