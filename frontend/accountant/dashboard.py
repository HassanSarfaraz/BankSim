# ===========================================================================
# Accountant Dashboard — Forest Green Theme
# Modules: Dashboard, Accounts, Transactions, Loans, Customers/KYC, Cards
# ===========================================================================
import tkinter as tk
from tkinter import ttk, messagebox
from frontend.utils.dashboard_base import DashboardBase
from frontend.utils.api_client import api
from frontend.styles import FONT_PRIMARY, FONT_BOLD, FONT_SUBTITLE, FONT_SMALL


class AccountantDashboard(DashboardBase):
    def __init__(self, on_logout=None):
        super().__init__("ACCOUNTANT", on_logout)

    def setup_sidebar(self):
        super().setup_sidebar()
        first = self.add_menu_item("Dashboard",     self.show_dashboard,   "📊")
        self.add_menu_item("Accounts",      self.show_accounts,    "💳")
        self.add_menu_item("Deposit",       self.show_deposit,     "📥")
        self.add_menu_item("Withdrawal",    self.show_withdrawal,  "📤")
        self.add_menu_item("Transfer",      self.show_transfer,    "🔄")
        self.add_menu_item("Loans",         self.show_loans,       "📋")
        self.add_menu_item("Customers",     self.show_customers,   "👤")
        self.add_menu_item("Cards",         self.show_cards,       "💳")
        self.add_spacer()
        self.add_logout()
        self._on_menu_click(first, self.show_dashboard)

    # ---- Dashboard ---------------------------------------------------------
    def show_dashboard(self):
        self.set_title("Accountant Overview")
        self.show_loading()
        api.async_call('GET', '/accountant/dashboard', self._render_dashboard, self.root)

    def _render_dashboard(self, result):
        self.clear_content()
        if not result.get("success"):
            return
        d = result["data"]
        self.create_kpi_row(self.content, [
            ("Today's Transactions", str(d.get("today_transactions", 0)), self.theme["accent"]),
            ("Pending Loans",        str(d.get("pending_loans", 0)),      "#E67E22"),
            ("Low Balance Alerts",   str(d.get("low_balance_alerts", 0)), self.theme["danger"]),
        ])

    # ---- Accounts ----------------------------------------------------------
    def show_accounts(self):
        self.set_title("Account Management")
        self.show_loading()
        api.async_call('GET', '/accountant/accounts', self._render_accounts, self.root)

    def _render_accounts(self, result):
        self.clear_content()
        if not result.get("success"):
            return

        bar = tk.Frame(self.content, bg=self.theme["content_bg"])
        bar.pack(fill="x", pady=(0, 10))
        self.create_button(bar, "+ Open Account", self._open_account_dialog)

        cols = [("account_id","Acc#",60),("customer_name","Customer",150),
                ("type","Type",100),("balance","Balance",120),
                ("status","Status",80),("branch_name","Branch",140)]
        for row in result["data"]:
            row["balance"] = f"PKR {row.get('balance',0):,.0f}"
        self.create_table(self.content, cols, result["data"])

    def _open_account_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("Open New Account")
        win.geometry("400x380")
        win.configure(bg="white")
        win.grab_set()

        fields = {}
        for label in ["Customer ID", "Branch ID", "Initial Deposit"]:
            tk.Label(win, text=label, font=FONT_PRIMARY, bg="white").pack(anchor="w", padx=30, pady=(8,0))
            e = ttk.Entry(win, width=35)
            e.pack(padx=30)
            fields[label] = e

        tk.Label(win, text="Account Type", font=FONT_PRIMARY, bg="white").pack(anchor="w", padx=30, pady=(8,0))
        type_var = tk.StringVar(value="savings")
        ttk.Combobox(win, textvariable=type_var, values=["savings","current","fixed_deposit"],
                     state="readonly", width=33).pack(padx=30)

        def submit():
            data = {
                "customer_id": int(fields["Customer ID"].get() or 0),
                "branch_id":   int(fields["Branch ID"].get() or 0),
                "type":        type_var.get(),
                "initial_deposit": float(fields["Initial Deposit"].get() or 0),
            }
            api.async_call('POST', '/accountant/accounts',
                           lambda r: self._on_created(r, win, "Account opened!"),
                           self.root, data=data)

        tk.Button(win, text="Open Account", font=FONT_BOLD,
                  bg=self.theme["accent"], fg="white", bd=0,
                  command=submit).pack(pady=20, ipady=6, ipadx=20)

    def _on_created(self, result, win, msg):
        if result.get("success"):
            win.destroy()
            messagebox.showinfo("Success", msg)
            self.show_accounts()
        else:
            messagebox.showerror("Error", result.get("error","Failed"))

    # ---- Deposit -----------------------------------------------------------
    def show_deposit(self):
        self.set_title("Cash Deposit")
        self._show_single_txn_form("deposit")

    # ---- Withdrawal --------------------------------------------------------
    def show_withdrawal(self):
        self.set_title("Cash Withdrawal")
        self._show_single_txn_form("withdrawal")

    def _show_single_txn_form(self, txn_type):
        self.clear_content()
        form = tk.Frame(self.content, bg="white",
                        highlightbackground="#E8E8E8", highlightthickness=1)
        form.pack(fill="x", pady=10)

        inner = tk.Frame(form, bg="white")
        inner.pack(padx=30, pady=25)

        tk.Label(inner, text=f"Cash {txn_type.capitalize()}", font=FONT_SUBTITLE,
                 bg="white", fg=self.theme["text"]).pack(anchor="w", pady=(0,10))

        fields = {}
        for label in ["Account ID", "Amount", "Description"]:
            tk.Label(inner, text=label, font=FONT_PRIMARY, bg="white").pack(anchor="w", pady=(6,0))
            e = ttk.Entry(inner, width=40)
            e.pack(anchor="w")
            fields[label] = e

        def submit():
            data = {
                "account_id": int(fields["Account ID"].get() or 0),
                "amount":     float(fields["Amount"].get() or 0),
                "description": fields["Description"].get(),
            }
            api.async_call('POST', f'/accountant/transactions/{txn_type}',
                           lambda r: self._txn_result(r, txn_type),
                           self.root, data=data)

        tk.Button(inner, text=f"Process {txn_type.capitalize()}", font=FONT_BOLD,
                  bg=self.theme["accent"], fg="white", bd=0,
                  command=submit).pack(pady=15, ipady=6, ipadx=20, anchor="w")

    def _txn_result(self, result, txn_type):
        if result.get("success"):
            messagebox.showinfo("Success", result.get("message", f"{txn_type} successful"))
        else:
            messagebox.showerror("Failed", result.get("message", result.get("error","Failed")))

    # ---- Transfer ----------------------------------------------------------
    def show_transfer(self):
        self.set_title("Fund Transfer")
        self.clear_content()

        form = tk.Frame(self.content, bg="white",
                        highlightbackground="#E8E8E8", highlightthickness=1)
        form.pack(fill="x", pady=10)
        inner = tk.Frame(form, bg="white")
        inner.pack(padx=30, pady=25)

        tk.Label(inner, text="Inter-Account Transfer", font=FONT_SUBTITLE,
                 bg="white").pack(anchor="w", pady=(0,10))

        fields = {}
        for label in ["From Account", "To Account", "Amount", "Description"]:
            tk.Label(inner, text=label, font=FONT_PRIMARY, bg="white").pack(anchor="w", pady=(6,0))
            e = ttk.Entry(inner, width=40)
            e.pack(anchor="w")
            fields[label] = e

        def submit():
            data = {
                "from_account": int(fields["From Account"].get() or 0),
                "to_account":   int(fields["To Account"].get() or 0),
                "amount":       float(fields["Amount"].get() or 0),
                "description":  fields["Description"].get(),
            }
            api.async_call('POST', '/accountant/transactions/transfer',
                           lambda r: self._txn_result(r, "transfer"),
                           self.root, data=data)

        tk.Button(inner, text="Execute Transfer", font=FONT_BOLD,
                  bg=self.theme["accent"], fg="white", bd=0,
                  command=submit).pack(pady=15, ipady=6, ipadx=20, anchor="w")

    # ---- Loans -------------------------------------------------------------
    def show_loans(self):
        self.set_title("Loan Management")
        self.show_loading()
        api.async_call('GET', '/accountant/loans', self._render_loans, self.root)

    def _render_loans(self, result):
        self.clear_content()
        if not result.get("success"):
            return

        bar = tk.Frame(self.content, bg=self.theme["content_bg"])
        bar.pack(fill="x", pady=(0,10))
        self.create_button(bar, "+ Create Loan", self._create_loan_dialog)

        cols = [("loan_id","ID",50),("customer_name","Customer",140),
                ("loan_type","Type",80),("amount","Amount",120),
                ("status","Status",80),("monthly_payment","Monthly",100)]
        for row in result["data"]:
            row["amount"] = f"PKR {row['amount']:,.0f}"
            row["monthly_payment"] = f"PKR {row.get('monthly_payment',0):,.0f}"
        self.create_table(self.content, cols, result["data"])

    def _create_loan_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("Create Loan")
        win.geometry("400x420")
        win.configure(bg="white")
        win.grab_set()

        fields = {}
        for label in ["Account ID", "Amount", "Interest Rate %", "Term (Months)"]:
            tk.Label(win, text=label, font=FONT_PRIMARY, bg="white").pack(anchor="w", padx=30, pady=(8,0))
            e = ttk.Entry(win, width=35)
            e.pack(padx=30)
            fields[label] = e

        tk.Label(win, text="Loan Type", font=FONT_PRIMARY, bg="white").pack(anchor="w", padx=30, pady=(8,0))
        type_var = tk.StringVar(value="personal")
        ttk.Combobox(win, textvariable=type_var, values=["personal","home","auto"],
                     state="readonly", width=33).pack(padx=30)

        def submit():
            data = {
                "account_id":    int(fields["Account ID"].get() or 0),
                "loan_type":     type_var.get(),
                "amount":        float(fields["Amount"].get() or 0),
                "interest_rate": float(fields["Interest Rate %"].get() or 0),
                "term_months":   int(fields["Term (Months)"].get() or 0),
            }
            api.async_call('POST', '/accountant/loans',
                           lambda r: self._on_created(r, win, "Loan created!"),
                           self.root, data=data)

        tk.Button(win, text="Submit Loan", font=FONT_BOLD,
                  bg=self.theme["accent"], fg="white", bd=0,
                  command=submit).pack(pady=20, ipady=6, ipadx=20)

    # ---- Customers / KYC ---------------------------------------------------
    def show_customers(self):
        self.set_title("Customer KYC Management")
        self.show_loading()
        api.async_call('GET', '/accountant/customers', self._render_customers, self.root)

    def _render_customers(self, result):
        self.clear_content()
        if not result.get("success"):
            return
        cols = [("customer_id","ID",50),("full_name","Name",160),
                ("cnic","CNIC",130),("phone","Phone",120),
                ("email","Email",180),("kyc_status","KYC",80)]
        self.create_table(self.content, cols, result["data"])

    # ---- Cards -------------------------------------------------------------
    def show_cards(self):
        self.set_title("Card Management")
        self.show_loading()
        api.async_call('GET', '/accountant/cards', self._render_cards, self.root)

    def _render_cards(self, result):
        self.clear_content()
        if not result.get("success"):
            return

        bar = tk.Frame(self.content, bg=self.theme["content_bg"])
        bar.pack(fill="x", pady=(0,10))
        self.create_button(bar, "+ Issue Card", self._issue_card_dialog)

        cols = [("card_id","ID",50),("card_number_masked","Card Number",180),
                ("card_type","Type",80),("status","Status",80),
                ("expiry_date","Expiry",100)]
        self.create_table(self.content, cols, result["data"])

    def _issue_card_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("Issue Card")
        win.geometry("380x280")
        win.configure(bg="white")
        win.grab_set()

        tk.Label(win, text="Account ID", font=FONT_PRIMARY, bg="white").pack(anchor="w", padx=30, pady=(15,0))
        acc_entry = ttk.Entry(win, width=35)
        acc_entry.pack(padx=30)

        tk.Label(win, text="Card Type", font=FONT_PRIMARY, bg="white").pack(anchor="w", padx=30, pady=(8,0))
        type_var = tk.StringVar(value="debit")
        ttk.Combobox(win, textvariable=type_var, values=["debit","credit"],
                     state="readonly", width=33).pack(padx=30)

        def submit():
            data = {"account_id": int(acc_entry.get() or 0), "card_type": type_var.get()}
            api.async_call('POST', '/accountant/cards',
                           lambda r: self._on_card_issued(r, win),
                           self.root, data=data)

        tk.Button(win, text="Issue Card", font=FONT_BOLD,
                  bg=self.theme["accent"], fg="white", bd=0,
                  command=submit).pack(pady=20, ipady=6, ipadx=20)

    def _on_card_issued(self, result, win):
        if result.get("success"):
            cvv = result.get("cvv", "???")
            win.destroy()
            messagebox.showinfo("Card Issued",
                                f"Card issued successfully!\nCVV: {cvv}\n(Save this — it won't be shown again)")
            self.show_cards()
        else:
            messagebox.showerror("Error", result.get("error","Failed"))
