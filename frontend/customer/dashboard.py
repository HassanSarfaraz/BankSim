# ===========================================================================
# Customer Dashboard — Indigo/Teal Self-Service Theme
# Modules: Dashboard, Transfer, Transactions, Loans, Cards, Profile
# ===========================================================================
import tkinter as tk
from tkinter import ttk, messagebox
from frontend.utils.dashboard_base import DashboardBase
from frontend.utils.api_client import api
from frontend.styles import FONT_PRIMARY, FONT_BOLD, FONT_SUBTITLE, FONT_SMALL, FONT_KPI


class CustomerDashboard(DashboardBase):
    def __init__(self, on_logout=None):
        super().__init__("CUSTOMER", on_logout)

    def setup_sidebar(self):
        super().setup_sidebar()
        first = self.add_menu_item("My Dashboard",  self.show_dashboard,    "🏠")
        self.add_menu_item("Fund Transfer", self.show_transfer,     "💸")
        self.add_menu_item("Transactions",  self.show_transactions, "📄")
        self.add_menu_item("Apply Loan",    self.show_apply_loan,   "📋")
        self.add_menu_item("My Loans",      self.show_my_loans,     "💰")
        self.add_menu_item("My Cards",      self.show_my_cards,     "💳")
        self.add_menu_item("Profile",       self.show_profile,      "👤")
        self.add_menu_item("Change Password", self.show_password,   "🔒")
        self.add_spacer()
        self.add_logout()
        self._on_menu_click(first, self.show_dashboard)

    # ---- Dashboard ---------------------------------------------------------
    def show_dashboard(self):
        self.set_title("My Dashboard")
        self.show_loading()
        api.async_call('GET', '/customer/accounts', self._render_dashboard, self.root)

    def _render_dashboard(self, result):
        self.clear_content()
        if not result.get("success"):
            tk.Label(self.content, text=result.get("error","Error loading accounts"),
                     fg="red", bg=self.theme["content_bg"]).pack(pady=50)
            return

        accounts = result["data"]
        if not accounts:
            tk.Label(self.content, text="No accounts found. Contact your branch.",
                     font=FONT_SUBTITLE, bg=self.theme["content_bg"],
                     fg=self.theme["text_muted"]).pack(pady=80)
            return

        # Balance cards
        kpis = []
        for acc in accounts:
            label = f"{acc['type'].capitalize()} (#{acc['account_id']})"
            value = f"PKR {acc['balance']:,.0f}"
            color = self.theme["accent"] if acc['status'] == 'active' else self.theme["danger"]
            kpis.append((label, value, color))

        self.create_kpi_row(self.content, kpis[:4])
        if len(kpis) > 4:
            self.create_kpi_row(self.content, kpis[4:])

        # Recent transactions
        tk.Label(self.content, text="Recent Transactions", font=FONT_SUBTITLE,
                 bg=self.theme["content_bg"], fg=self.theme["text"]).pack(
                     anchor="w", pady=(15, 5))
        api.async_call('GET', '/customer/transactions', self._render_recent_txns,
                       self.root, params={"limit": 10})

    def _render_recent_txns(self, result):
        if not result.get("success") or not result.get("data"):
            tk.Label(self.content, text="No recent transactions",
                     font=FONT_SMALL, bg=self.theme["content_bg"],
                     fg=self.theme["text_muted"]).pack(anchor="w")
            return
        cols = [("txn_id","#",50),("txn_type","Type",100),
                ("amount","Amount",120),("status","Status",80),
                ("timestamp","Date",160)]
        for r in result["data"]:
            r["amount"] = f"PKR {r['amount']:,.0f}"
        self.create_table(self.content, cols, result["data"], height=8)

    # ---- Fund Transfer -----------------------------------------------------
    def show_transfer(self):
        self.set_title("Fund Transfer")
        self.clear_content()

        form = tk.Frame(self.content, bg="white",
                        highlightbackground="#E8E8E8", highlightthickness=1)
        form.pack(fill="x", pady=10)
        inner = tk.Frame(form, bg="white")
        inner.pack(padx=30, pady=25)

        tk.Label(inner, text="Send Money", font=FONT_SUBTITLE,
                 bg="white", fg=self.theme["text"]).pack(anchor="w", pady=(0,10))

        fields = {}
        for label in ["From Account (Your Acc#)", "To Account", "Amount", "Description"]:
            tk.Label(inner, text=label, font=FONT_PRIMARY, bg="white").pack(anchor="w", pady=(6,0))
            e = ttk.Entry(inner, width=40)
            e.pack(anchor="w")
            fields[label] = e

        def submit():
            data = {
                "from_account": int(fields["From Account (Your Acc#)"].get() or 0),
                "to_account":   int(fields["To Account"].get() or 0),
                "amount":       float(fields["Amount"].get() or 0),
                "description":  fields["Description"].get() or "Online transfer",
            }
            if messagebox.askyesno("Confirm Transfer",
                                   f"Transfer PKR {data['amount']:,.0f}\n"
                                   f"From: #{data['from_account']}\n"
                                   f"To:   #{data['to_account']}\n\nProceed?"):
                api.async_call('POST', '/customer/transfer',
                               self._transfer_result, self.root, data=data)

        tk.Button(inner, text="Send Money", font=FONT_BOLD,
                  bg=self.theme["accent"], fg="white", bd=0,
                  command=submit).pack(pady=15, ipady=6, ipadx=20, anchor="w")

    def _transfer_result(self, result):
        if result.get("success"):
            messagebox.showinfo("Success", result.get("message","Transfer successful!"))
            self.show_dashboard()
        else:
            messagebox.showerror("Transfer Failed",
                                 result.get("message", result.get("error","Failed")))

    # ---- Transactions History ----------------------------------------------
    def show_transactions(self):
        self.set_title("Transaction History")
        self.show_loading()
        api.async_call('GET', '/customer/transactions', self._render_txns,
                       self.root, params={"limit": 100})

    def _render_txns(self, result):
        self.clear_content()
        if not result.get("success"):
            return
        cols = [("txn_id","#",50),("txn_type","Type",100),
                ("from_account","From",70),("to_account","To",70),
                ("amount","Amount",120),("status","Status",80),
                ("description","Description",200),("timestamp","Date",160)]
        for r in result["data"]:
            r["amount"] = f"PKR {r['amount']:,.0f}"
        self.create_table(self.content, cols, result["data"])

    # ---- Apply for Loan ----------------------------------------------------
    def show_apply_loan(self):
        self.set_title("Apply for a Loan")
        self.clear_content()

        form = tk.Frame(self.content, bg="white",
                        highlightbackground="#E8E8E8", highlightthickness=1)
        form.pack(fill="x", pady=10)
        inner = tk.Frame(form, bg="white")
        inner.pack(padx=30, pady=25)

        tk.Label(inner, text="Loan Application", font=FONT_SUBTITLE,
                 bg="white").pack(anchor="w", pady=(0,10))

        fields = {}
        for label in ["Account ID", "Amount (PKR)", "Term (Months)"]:
            tk.Label(inner, text=label, font=FONT_PRIMARY, bg="white").pack(anchor="w", pady=(6,0))
            e = ttk.Entry(inner, width=40)
            e.pack(anchor="w")
            fields[label] = e

        tk.Label(inner, text="Loan Type", font=FONT_PRIMARY, bg="white").pack(anchor="w", pady=(6,0))
        type_var = tk.StringVar(value="personal")
        ttk.Combobox(inner, textvariable=type_var,
                     values=["personal","home","auto"],
                     state="readonly", width=38).pack(anchor="w")

        def submit():
            data = {
                "account_id":  int(fields["Account ID"].get() or 0),
                "loan_type":   type_var.get(),
                "amount":      float(fields["Amount (PKR)"].get() or 0),
                "term_months": int(fields["Term (Months)"].get() or 0),
            }
            api.async_call('POST', '/customer/loans/apply',
                           self._loan_result, self.root, data=data)

        tk.Button(inner, text="Submit Application", font=FONT_BOLD,
                  bg=self.theme["accent"], fg="white", bd=0,
                  command=submit).pack(pady=15, ipady=6, ipadx=20, anchor="w")

    def _loan_result(self, result):
        if result.get("success"):
            messagebox.showinfo("Submitted", "Loan application submitted for review!")
            self.show_my_loans()
        else:
            messagebox.showerror("Error", result.get("error","Failed"))

    # ---- My Loans ----------------------------------------------------------
    def show_my_loans(self):
        self.set_title("My Loans")
        self.show_loading()
        api.async_call('GET', '/customer/loans', self._render_my_loans, self.root)

    def _render_my_loans(self, result):
        self.clear_content()
        if not result.get("success"):
            return
        data = result["data"]
        if not data:
            tk.Label(self.content, text="No loan applications found.",
                     font=FONT_SUBTITLE, bg=self.theme["content_bg"],
                     fg=self.theme["text_muted"]).pack(pady=80)
            return

        cols = [("loan_id","ID",50),("loan_type","Type",80),
                ("amount","Amount",120),("status","Status",90),
                ("monthly_payment","Monthly",100),
                ("amount_remaining","Remaining",120)]
        for r in data:
            r["amount"] = f"PKR {r['amount']:,.0f}"
            r["monthly_payment"] = f"PKR {r.get('monthly_payment',0):,.0f}"
            r["amount_remaining"] = f"PKR {r.get('amount_remaining',0):,.0f}"
        self.create_table(self.content, cols, data)

    # ---- My Cards ----------------------------------------------------------
    def show_my_cards(self):
        self.set_title("My Cards")
        self.show_loading()
        api.async_call('GET', '/customer/cards', self._render_my_cards, self.root)

    def _render_my_cards(self, result):
        self.clear_content()
        if not result.get("success"):
            return
        data = result["data"]
        if not data:
            tk.Label(self.content, text="No cards linked to your accounts.",
                     font=FONT_SUBTITLE, bg=self.theme["content_bg"],
                     fg=self.theme["text_muted"]).pack(pady=80)
            return
        cols = [("card_id","ID",50),("card_number_masked","Card Number",200),
                ("card_type","Type",80),("status","Status",80),
                ("expiry_date","Expiry",100)]
        self.create_table(self.content, cols, data)

    # ---- Profile -----------------------------------------------------------
    def show_profile(self):
        self.set_title("My Profile")
        self.show_loading()
        api.async_call('GET', '/customer/profile', self._render_profile, self.root)

    def _render_profile(self, result):
        self.clear_content()
        if not result.get("success"):
            return

        p = result["data"]
        card = tk.Frame(self.content, bg="white",
                        highlightbackground="#E8E8E8", highlightthickness=1)
        card.pack(fill="x", pady=10)
        inner = tk.Frame(card, bg="white")
        inner.pack(padx=30, pady=25, fill="x")

        fields_data = [
            ("Full Name",  p.get("full_name", "")),
            ("CNIC",       p.get("cnic", "")),
            ("Date of Birth", p.get("dob", "")),
            ("Phone",      p.get("phone", "")),
            ("Email",      p.get("email", "")),
            ("KYC Status", p.get("kyc_status", "")),
        ]
        for label, value in fields_data:
            row = tk.Frame(inner, bg="white")
            row.pack(fill="x", pady=3)
            tk.Label(row, text=f"{label}:", font=FONT_BOLD, bg="white",
                     fg=self.theme["text"], width=15, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=FONT_PRIMARY, bg="white",
                     fg=self.theme["text_muted"]).pack(side="left")

    # ---- Change Password ---------------------------------------------------
    def show_password(self):
        self.set_title("Change Password")
        self.clear_content()

        form = tk.Frame(self.content, bg="white",
                        highlightbackground="#E8E8E8", highlightthickness=1)
        form.pack(fill="x", pady=10)
        inner = tk.Frame(form, bg="white")
        inner.pack(padx=30, pady=25)

        tk.Label(inner, text="Change Your Password", font=FONT_SUBTITLE,
                 bg="white").pack(anchor="w", pady=(0,10))

        fields = {}
        for label in ["Current Password", "New Password", "Confirm New Password"]:
            tk.Label(inner, text=label, font=FONT_PRIMARY, bg="white").pack(anchor="w", pady=(6,0))
            e = ttk.Entry(inner, width=40, show="*")
            e.pack(anchor="w")
            fields[label] = e

        def submit():
            old = fields["Current Password"].get()
            new = fields["New Password"].get()
            confirm = fields["Confirm New Password"].get()
            if new != confirm:
                messagebox.showerror("Error", "New passwords do not match")
                return
            if len(new) < 6:
                messagebox.showerror("Error", "Password must be at least 6 characters")
                return
            api.async_call('PUT', '/customer/password',
                           self._pw_result, self.root,
                           data={"old_password": old, "new_password": new})

        tk.Button(inner, text="Update Password", font=FONT_BOLD,
                  bg=self.theme["accent"], fg="white", bd=0,
                  command=submit).pack(pady=15, ipady=6, ipadx=20, anchor="w")

    def _pw_result(self, result):
        if result.get("success"):
            messagebox.showinfo("Success", "Password changed successfully!")
        else:
            messagebox.showerror("Error", result.get("error","Failed"))
