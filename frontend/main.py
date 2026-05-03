# ===========================================================================
# SecureBank — Tkinter Login Screen & Role Router
# Entry point for the GUI. Run:  python -m frontend.main
# ===========================================================================
import tkinter as tk
from tkinter import ttk, messagebox
from frontend.styles import THEMES, FONT_FAMILY, FONT_PRIMARY, FONT_BOLD, FONT_HEADER
from frontend.utils.api_client import api


class LoginWindow:
    """Premium login screen with gradient-style branding."""

    def __init__(self, root):
        self.root = root
        self.root.title("SecureBank — Login")
        self.root.geometry("440x560")
        self.root.resizable(False, False)
        self.root.configure(bg="#FFFFFF")

        # Center on screen
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        root.geometry(f"440x560+{(sw-440)//2}+{(sh-560)//2}")

        self._build_ui()

    def _build_ui(self):
        # ---- Brand header (colored band) -----------------------------------
        brand = tk.Frame(self.root, height=130, bg="#0F2A4A")
        brand.pack(fill="x")
        brand.pack_propagate(False)

        tk.Label(brand, text="🏦", font=(FONT_FAMILY, 32),
                 bg="#0F2A4A", fg="white").pack(pady=(20, 0))
        tk.Label(brand, text="SecureBank", font=(FONT_FAMILY, 22, "bold"),
                 bg="#0F2A4A", fg="white").pack()
        tk.Label(brand, text="Management System",
                 font=(FONT_FAMILY, 9),
                 bg="#0F2A4A", fg="#8EAACC").pack()

        # ---- Form card -----------------------------------------------------
        card = tk.Frame(self.root, bg="#FFFFFF")
        card.pack(fill="both", expand=True, padx=40, pady=25)

        tk.Label(card, text="Sign In", font=(FONT_FAMILY, 16, "bold"),
                 bg="#FFFFFF", fg="#2C3E50").pack(anchor="w", pady=(0, 15))

        # Username
        tk.Label(card, text="Username", font=FONT_PRIMARY,
                 bg="#FFFFFF", fg="#7F8C8D").pack(anchor="w")
        self.username_entry = ttk.Entry(card, width=35, font=FONT_PRIMARY)
        self.username_entry.pack(fill="x", ipady=6, pady=(2, 12))
        self.username_entry.focus_set()

        # Password
        tk.Label(card, text="Password", font=FONT_PRIMARY,
                 bg="#FFFFFF", fg="#7F8C8D").pack(anchor="w")
        self.password_entry = ttk.Entry(card, width=35, show="●",
                                         font=FONT_PRIMARY)
        self.password_entry.pack(fill="x", ipady=6, pady=(2, 20))

        # Bind Enter key
        self.password_entry.bind("<Return>", lambda e: self._handle_login())

        # Login button
        self.login_btn = tk.Button(
            card, text="LOGIN", font=(FONT_FAMILY, 11, "bold"),
            bg="#0F2A4A", fg="white", activebackground="#1B3A6B",
            activeforeground="white", bd=0, cursor="hand2",
            command=self._handle_login,
        )
        self.login_btn.pack(fill="x", ipady=10, pady=(0, 10))
        self.login_btn.bind("<Enter>", lambda e: self.login_btn.config(bg="#1B3A6B"))
        self.login_btn.bind("<Leave>", lambda e: self.login_btn.config(bg="#0F2A4A"))

        # Status label
        self.status_label = tk.Label(card, text="", font=(FONT_FAMILY, 9),
                                      bg="#FFFFFF", fg="#E74C3C")
        self.status_label.pack()

        # ---- Footer --------------------------------------------------------
        tk.Label(self.root, text="© 2026 GIK Institute  |  CS232 Project",
                 font=(FONT_FAMILY, 8), bg="#FFFFFF",
                 fg="#BDC3C7").pack(side="bottom", pady=10)

    def _handle_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            self.status_label.config(text="Please enter username and password")
            return

        self.status_label.config(text="Authenticating...", fg="#3498DB")
        self.login_btn.config(state="disabled", text="Signing in...")
        self.root.update_idletasks()

        # Run login in background thread
        import threading

        def _do_login():
            success, msg, role = api.login(username, password)
            self.root.after(0, lambda: self._on_login_result(success, msg, role))

        threading.Thread(target=_do_login, daemon=True).start()

    def _on_login_result(self, success, msg, role):
        self.login_btn.config(state="normal", text="LOGIN")

        if success:
            self.status_label.config(text="")
            self.root.withdraw()
            self._launch_dashboard(role.upper())
        else:
            self.status_label.config(text=msg, fg="#E74C3C")

    def _launch_dashboard(self, role):
        from frontend.manager.dashboard import ManagerDashboard
        from frontend.accountant.dashboard import AccountantDashboard
        from frontend.customer.dashboard import CustomerDashboard

        def on_logout():
            """Called when dashboard closes — show login again."""
            self.root.deiconify()
            self.password_entry.delete(0, "end")
            self.status_label.config(text="Logged out", fg="#27AE60")

        if role == "MANAGER":
            ManagerDashboard(on_logout=on_logout)
        elif role == "ACCOUNTANT":
            AccountantDashboard(on_logout=on_logout)
        elif role == "CUSTOMER":
            CustomerDashboard(on_logout=on_logout)


# ---------------------------------------------------------------------------
# Entry point:  python -m frontend.main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = LoginWindow(root)
    root.mainloop()
