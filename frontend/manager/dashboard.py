# ===========================================================================
# Manager Dashboard — Navy Blue Theme
# Modules: Dashboard, Employees, Branches, Customers, Loans, Audit, Config
# ===========================================================================
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from frontend.utils.dashboard_base import DashboardBase
from frontend.utils.api_client import api
from frontend.styles import FONT_PRIMARY, FONT_BOLD, FONT_SUBTITLE, FONT_SMALL


class ManagerDashboard(DashboardBase):
    def __init__(self, on_logout=None):
        super().__init__("MANAGER", on_logout)

    def setup_sidebar(self):
        super().setup_sidebar()
        first = self.add_menu_item("Dashboard",      self.show_dashboard, "📊")
        self.add_menu_item("Employees",     self.show_employees,  "👥")
        self.add_menu_item("Branches",      self.show_branches,   "🏢")
        self.add_menu_item("Customers",     self.show_customers,  "👤")
        self.add_menu_item("Loan Approvals",self.show_loans,      "📋")
        self.add_menu_item("System Config", self.show_config,     "⚙")
        self.add_menu_item("Audit Logs",    self.show_audit,      "📜")
        self.add_spacer()
        self.add_logout()
        # Auto-click first item
        self._on_menu_click(first, self.show_dashboard)

    # ---- Dashboard ---------------------------------------------------------
    def show_dashboard(self):
        self.set_title("System Overview")
        self.show_loading()
        api.async_call('GET', '/manager/dashboard', self._render_dashboard, self.root)

    def _render_dashboard(self, result):
        self.clear_content()
        if not result.get("success"):
            tk.Label(self.content, text=f"Error: {result.get('error','')}",
                     fg="red", bg=self.theme["content_bg"]).pack(pady=50)
            return

        d = result["data"]
        self.create_kpi_row(self.content, [
            ("Total Assets",     f"PKR {d['total_assets']:,.0f}",  self.theme["accent"]),
            ("Active Accounts",  str(d['active_accounts']),        self.theme["text"]),
            ("Loan Portfolio",   f"PKR {d['loan_portfolio']:,.0f}",self.theme["success"]),
            ("Today's Volume",   f"PKR {d['daily_volume']:,.0f}", "#3498DB"),
        ])
        self.create_kpi_row(self.content, [
            ("Total Customers",  str(d.get('total_customers', 0)), self.theme["accent"]),
            ("Total Branches",   str(d.get('total_branches', 0)),  self.theme["text"]),
        ])

    # ---- Employees ---------------------------------------------------------
    def show_employees(self):
        self.set_title("Employee Management")
        self.show_loading()
        api.async_call('GET', '/manager/employees', self._render_employees, self.root)

    def _render_employees(self, result):
        self.clear_content()
        if not result.get("success"):
            return

        # Action bar
        bar = tk.Frame(self.content, bg=self.theme["content_bg"])
        bar.pack(fill="x", pady=(0, 10))
        self.create_button(bar, "+ Add Employee", self._add_employee_dialog)

        cols = [("employee_id","ID",50),("full_name","Name",180),
                ("designation","Designation",150),("branch_name","Branch",150),
                ("is_active","Active",80)]
        self.create_table(self.content, cols, result["data"])

    def _add_employee_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("Add Employee")
        win.geometry("400x420")
        win.configure(bg="white")
        win.grab_set()

        fields = {}
        for label in ["Username", "Password", "Full Name", "Designation", "Branch ID"]:
            tk.Label(win, text=label, font=FONT_PRIMARY, bg="white").pack(anchor="w", padx=30, pady=(8,0))
            e = ttk.Entry(win, width=35)
            if label == "Password":
                e.config(show="*")
            e.pack(padx=30)
            fields[label] = e

        def submit():
            data = {
                "username":    fields["Username"].get(),
                "password":    fields["Password"].get(),
                "full_name":   fields["Full Name"].get(),
                "designation": fields["Designation"].get(),
                "branch_id":   int(fields["Branch ID"].get() or 0),
            }
            api.async_call('POST', '/manager/employees',
                           lambda r: self._on_emp_created(r, win), self.root, data=data)

        tk.Button(win, text="Create Employee", font=FONT_BOLD,
                  bg=self.theme["accent"], fg="white", bd=0,
                  command=submit).pack(pady=20, ipady=6, ipadx=20)

    def _on_emp_created(self, result, win):
        if result.get("success"):
            win.destroy()
            messagebox.showinfo("Success", "Employee created!")
            self.show_employees()
        else:
            messagebox.showerror("Error", result.get("error", "Failed"))

    # ---- Branches ----------------------------------------------------------
    def show_branches(self):
        self.set_title("Branch Management")
        self.show_loading()
        api.async_call('GET', '/manager/branches', self._render_branches, self.root)

    def _render_branches(self, result):
        self.clear_content()
        if not result.get("success"):
            return
        cols = [("branch_id","ID",50),("name","Name",180),
                ("city","City",120),("total_accounts","Accounts",80),
                ("total_deposits","Total Deposits",140)]
        for row in result["data"]:
            row["total_deposits"] = f"PKR {row.get('total_deposits',0):,.0f}"
        self.create_table(self.content, cols, result["data"])

    # ---- Customers ---------------------------------------------------------
    def show_customers(self):
        self.set_title("Customer Oversight")
        self.show_loading()
        api.async_call('GET', '/manager/customers', self._render_customers, self.root)

    def _render_customers(self, result):
        self.clear_content()
        if not result.get("success"):
            return
        cols = [("customer_id","ID",50),("full_name","Name",160),
                ("cnic","CNIC",130),("phone","Phone",120),
                ("kyc_status","KYC",80)]
        self.create_table(self.content, cols, result["data"])

    # ---- Loan Approvals ----------------------------------------------------
    def show_loans(self):
        self.set_title("Pending Loan Approvals")
        self.show_loading()
        api.async_call('GET', '/manager/loans/pending', self._render_loans, self.root)

    def _render_loans(self, result):
        self.clear_content()
        if not result.get("success"):
            return

        data = result["data"]
        if not data:
            tk.Label(self.content, text="No pending loan applications ✓",
                     font=FONT_SUBTITLE, bg=self.theme["content_bg"],
                     fg=self.theme["success"]).pack(pady=80)
            return

        for loan in data:
            card = tk.Frame(self.content, bg="white",
                            highlightbackground="#E8E8E8", highlightthickness=1)
            card.pack(fill="x", pady=4)

            info = tk.Frame(card, bg="white")
            info.pack(fill="x", padx=20, pady=12)

            left = tk.Frame(info, bg="white")
            left.pack(side="left")
            tk.Label(left, text=f"Loan #{loan['loan_id']} — {loan['loan_type'].upper()}",
                     font=FONT_BOLD, bg="white", fg=self.theme["text"]).pack(anchor="w")
            tk.Label(left, text=f"Amount: PKR {loan['amount']:,.0f}  |  Term: {loan['term_months']}mo  |  Customer: {loan.get('customer_name','N/A')}",
                     font=FONT_SMALL, bg="white", fg=self.theme["text_muted"]).pack(anchor="w")

            btns = tk.Frame(info, bg="white")
            btns.pack(side="right")

            def approve(lid=loan['loan_id']):
                reason = simpledialog.askstring("Approve", "Reason for approval:", parent=self.root)
                if reason:
                    api.async_call('PUT', f'/manager/loans/{lid}/decide',
                                   lambda r: self._after_decide(r), self.root,
                                   data={"decision":"approve","reason":reason})

            def reject(lid=loan['loan_id']):
                reason = simpledialog.askstring("Reject", "Reason for rejection:", parent=self.root)
                if reason:
                    api.async_call('PUT', f'/manager/loans/{lid}/decide',
                                   lambda r: self._after_decide(r), self.root,
                                   data={"decision":"reject","reason":reason})

            tk.Button(btns, text="✓ Approve", font=FONT_SMALL, bg=self.theme["success"],
                      fg="white", bd=0, command=approve, cursor="hand2").pack(side="left", padx=4, ipady=4, ipadx=8)
            tk.Button(btns, text="✗ Reject",  font=FONT_SMALL, bg=self.theme["danger"],
                      fg="white", bd=0, command=reject,  cursor="hand2").pack(side="left", ipady=4, ipadx=8)

    def _after_decide(self, result):
        if result.get("success"):
            messagebox.showinfo("Done", "Loan decision recorded.")
            self.show_loans()
        else:
            messagebox.showerror("Error", result.get("error","Failed"))

    # ---- System Configuration -----------------------------------------------
    def show_config(self):
        self.set_title("System Configuration")
        self.show_loading()
        api.async_call('GET', '/manager/policies', self._render_config, self.root)

    def _render_config(self, result):
        self.clear_content()
        if not result.get("success"):
            return
        cols = [("acc_type","Account Type",150),
                ("daily_withdrawal_limit","Daily Limit",140),
                ("interest_rate","Interest Rate %",120),
                ("min_balance","Min Balance",120),
                ("overdraft_allowed","Overdraft",100)]
        for row in result["data"]:
            row["daily_withdrawal_limit"] = f"PKR {row['daily_withdrawal_limit']:,.0f}"
            row["min_balance"] = f"PKR {row['min_balance']:,.0f}"
            row["overdraft_allowed"] = "Yes" if row["overdraft_allowed"] else "No"
        self.create_table(self.content, cols, result["data"])

    # ---- Audit Logs (MongoDB) -----------------------------------------------
    def show_audit(self):
        self.set_title("Audit Logs (MongoDB)")
        self.show_loading()
        api.async_call('GET', '/manager/audit', self._render_audit, self.root)

    def _render_audit(self, result):
        self.clear_content()
        if not result.get("success"):
            return
        cols = [("timestamp","Timestamp",170),("user_id","User",60),
                ("action","Action",160),("details","Details",350)]
        self.create_table(self.content, cols, result.get("data", []))
