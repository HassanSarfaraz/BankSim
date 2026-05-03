# ===========================================================================
# SecureBank — Dashboard Base Class (all three roles inherit from this)
# Provides: themed sidebar, content area, header, KPI cards, data tables.
# ===========================================================================
import tkinter as tk
from tkinter import ttk, messagebox
from frontend.styles import (
    THEMES, FONT_FAMILY, FONT_PRIMARY, FONT_BOLD, FONT_TITLE,
    FONT_SUBTITLE, FONT_HEADER, FONT_KPI, FONT_MENU, FONT_SMALL
)
from frontend.utils.api_client import api


class DashboardBase:
    """Base class for Manager / Accountant / Customer dashboards."""

    def __init__(self, role, on_logout=None):
        self.role = role
        self.theme = THEMES[role]
        self.on_logout = on_logout
        self._menu_buttons = []
        self._active_btn = None

        self.root = tk.Toplevel()
        self.root.title(f"SecureBank — {role.capitalize()}")
        self.root.geometry("1200x750")
        self.root.minsize(1000, 600)
        self.root.configure(bg=self.theme["content_bg"])

        # Center
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"1200x750+{(sw-1200)//2}+{(sh-750)//2}")

        self._build_layout()
        self.setup_sidebar()

    # ---- layout skeleton ---------------------------------------------------
    def _build_layout(self):
        # Sidebar frame
        self.sidebar = tk.Frame(self.root, width=240,
                                bg=self.theme["sidebar_bg"])
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Right pane
        right = tk.Frame(self.root, bg=self.theme["content_bg"])
        right.pack(side="right", expand=True, fill="both")

        # Header bar
        self.header = tk.Frame(right, height=65, bg=self.theme["header_bg"])
        self.header.pack(side="top", fill="x")
        self.header.pack_propagate(False)

        # Shadow line under header
        tk.Frame(right, height=1, bg="#E0E0E0").pack(side="top", fill="x")

        self.title_label = tk.Label(
            self.header, text="Dashboard", font=FONT_TITLE,
            bg=self.theme["header_bg"], fg=self.theme["text"]
        )
        self.title_label.pack(side="left", padx=30, pady=15)

        self.user_label = tk.Label(
            self.header,
            text=f"  {api.user['username']}  |  {self.role.capitalize()}",
            font=FONT_SMALL, bg=self.theme["header_bg"],
            fg=self.theme["text_muted"]
        )
        self.user_label.pack(side="right", padx=20)

        # Content area (scrollable)
        self.content_wrapper = tk.Frame(right, bg=self.theme["content_bg"])
        self.content_wrapper.pack(expand=True, fill="both")

        self.content = tk.Frame(self.content_wrapper,
                                bg=self.theme["content_bg"])
        self.content.pack(expand=True, fill="both", padx=25, pady=15)

    # ---- sidebar helpers ---------------------------------------------------
    def setup_sidebar(self):
        """Override in subclass to add menu items."""
        # Brand
        brand_frame = tk.Frame(self.sidebar, bg=self.theme["sidebar_bg"])
        brand_frame.pack(fill="x", pady=(25, 30))
        tk.Label(brand_frame, text="🏦", font=(FONT_FAMILY, 22),
                 bg=self.theme["sidebar_bg"], fg="white").pack()
        tk.Label(brand_frame, text="SecureBank", font=(FONT_FAMILY, 16, "bold"),
                 bg=self.theme["sidebar_bg"], fg="white").pack()
        tk.Frame(self.sidebar, height=1,
                 bg=self.theme["sidebar_hover"]).pack(fill="x", padx=15)

    def add_menu_item(self, text, command, icon=""):
        """Add a sidebar button. Returns the button widget."""
        display = f"  {icon}  {text}" if icon else f"     {text}"
        btn = tk.Button(
            self.sidebar, text=display, anchor="w", font=FONT_MENU,
            bg=self.theme["sidebar_bg"], fg="#CBD5E1",
            bd=0, relief="flat",
            activebackground=self.theme["sidebar_hover"],
            activeforeground="white",
            cursor="hand2",
            command=lambda b=None, c=command: self._on_menu_click(b, c),
        )
        btn.pack(fill="x", pady=1, padx=8, ipady=8)

        # Hover effects
        btn.bind("<Enter>", lambda e, b=btn: b.config(
            bg=self.theme["sidebar_hover"], fg="white"))
        btn.bind("<Leave>", lambda e, b=btn: b.config(
            bg=self.theme["accent"] if b == self._active_btn
            else self.theme["sidebar_bg"],
            fg="white" if b == self._active_btn else "#CBD5E1"))

        # Re-bind command with the actual button reference
        btn.config(command=lambda b=btn, c=command: self._on_menu_click(b, c))
        self._menu_buttons.append(btn)
        return btn

    def add_spacer(self):
        tk.Frame(self.sidebar, bg=self.theme["sidebar_bg"]).pack(
            expand=True, fill="both")

    def add_logout(self):
        tk.Frame(self.sidebar, height=1,
                 bg=self.theme["sidebar_hover"]).pack(fill="x", padx=15, pady=5)
        self.add_menu_item("Logout", self._do_logout, icon="⏻")

    def _on_menu_click(self, btn, command):
        # Highlight active
        if self._active_btn:
            self._active_btn.config(bg=self.theme["sidebar_bg"], fg="#CBD5E1")
        if btn:
            btn.config(bg=self.theme["accent"], fg="white")
            self._active_btn = btn
        command()

    def _do_logout(self):
        self.root.destroy()
        if self.on_logout:
            self.on_logout()

    # ---- content helpers ---------------------------------------------------
    def set_title(self, text):
        self.title_label.config(text=text)

    def clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def show_loading(self, message="Loading..."):
        self.clear_content()
        tk.Label(self.content, text=message, font=FONT_SUBTITLE,
                 bg=self.theme["content_bg"],
                 fg=self.theme["text_muted"]).pack(pady=100)

    # ---- KPI card row (used by all dashboards) -----------------------------
    def create_kpi_row(self, parent, kpis):
        """
        kpis: list of (label, value, color) tuples.
        Creates a horizontal row of styled metric cards.
        """
        row = tk.Frame(parent, bg=self.theme["content_bg"])
        row.pack(fill="x", pady=(0, 15))

        for i, (label, value, color) in enumerate(kpis):
            card = tk.Frame(row, bg=self.theme["card_bg"],
                            highlightbackground="#E8E8E8",
                            highlightthickness=1)
            card.pack(side="left", expand=True, fill="x",
                      padx=(0 if i == 0 else 6, 0))

            inner = tk.Frame(card, bg=self.theme["card_bg"])
            inner.pack(padx=20, pady=18, fill="x")

            tk.Label(inner, text=label, font=FONT_SMALL,
                     bg=self.theme["card_bg"],
                     fg=self.theme["text_muted"]).pack(anchor="w")
            tk.Label(inner, text=str(value), font=FONT_KPI,
                     bg=self.theme["card_bg"], fg=color).pack(anchor="w")

    # ---- Data table --------------------------------------------------------
    def create_table(self, parent, columns, data, height=12):
        """
        columns: list of (col_id, header_text, width)
        data:    list of dicts
        Returns the Treeview widget.
        """
        frame = tk.Frame(parent, bg=self.theme["card_bg"],
                         highlightbackground="#E8E8E8",
                         highlightthickness=1)
        frame.pack(fill="both", expand=True, pady=(0, 10))

        style = ttk.Style()
        style.configure("Bank.Treeview", font=FONT_PRIMARY, rowheight=30,
                         background=self.theme["card_bg"],
                         fieldbackground=self.theme["card_bg"])
        style.configure("Bank.Treeview.Heading", font=FONT_BOLD)

        col_ids = [c[0] for c in columns]
        tree = ttk.Treeview(frame, columns=col_ids, show="headings",
                            height=height, style="Bank.Treeview")

        for col_id, header, width in columns:
            tree.heading(col_id, text=header)
            tree.column(col_id, width=width, minwidth=60)

        for row in data:
            vals = [row.get(c[0], "") for c in columns]
            tree.insert("", "end", values=vals)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True, padx=1, pady=1)

        return tree

    # ---- Action button row -------------------------------------------------
    def create_button(self, parent, text, command, color=None, width=15):
        bg = color or self.theme["accent"]
        btn = tk.Button(parent, text=text, font=FONT_BOLD,
                        bg=bg, fg="white", bd=0, cursor="hand2",
                        command=command, width=width)
        btn.pack(side="left", padx=(0, 8), ipady=6)
        btn.bind("<Enter>", lambda e: btn.config(bg=self.theme.get("accent_hover", bg)))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn
