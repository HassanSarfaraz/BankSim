import tkinter as tk
from tkinter import ttk, messagebox
import requests

class AccountantDashboard(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg="#F0F4F0")
        
        self.setup_ui()

    def setup_ui(self):
        # Sidebar
        sidebar = tk.Frame(self, bg="#2E7D32", width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="SecureBank", fg="white", bg="#2E7D32", font=("Helvetica", 16, "bold")).pack(pady=30)

        buttons = ["Dashboard", "Accounts", "Transactions", "Loans", "KYC"]
        for btn_text in buttons:
            tk.Button(sidebar, text=btn_text, bg="#2E7D32", fg="white", relief="flat", 
                      padx=20, pady=10, anchor="w", cursor="hand2").pack(fill="x")

        tk.Button(sidebar, text="Logout", command=self.controller.show_login, 
                  bg="#1B5E20", fg="white", relief="flat", pady=10).pack(side="bottom", fill="x")

        # Main Content
        self.main_area = tk.Frame(self, bg="#F0F4F0", padx=30, pady=30)
        self.main_area.pack(side="right", fill="both", expand=True)

        tk.Label(self.main_area, text="Accountant Dashboard", font=("Helvetica", 24, "bold"), bg="#F0F4F0", fg="#2E7D32").pack(anchor="w")
        
        # Stats Row
        stats_frame = tk.Frame(self.main_area, bg="#F0F4F0")
        stats_frame.pack(fill="x", pady=20)

        self.create_stat_card(stats_frame, "Total Accounts", "1,245", 0)
        self.create_stat_card(stats_frame, "Pending Loans", "12", 1)
        self.create_stat_card(stats_frame, "Today's TXNs", "48", 2)

        # Account List
        tk.Label(self.main_area, text="Recent Accounts", font=("Helvetica", 14, "bold"), bg="#F0F4F0").pack(anchor="w", pady=(20, 10))
        
        # Treeview for accounts
        columns = ("ID", "Customer", "Type", "Balance", "Status")
        self.tree = ttk.Treeview(self.main_area, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        
        self.tree.pack(fill="both", expand=True)
        self.refresh_data()

    def create_stat_card(self, parent, label, value, col):
        card = tk.Frame(parent, bg="white", padx=20, pady=20, highlightbackground="#E0E0E0", highlightthickness=1)
        card.grid(row=0, column=col, padx=(0, 20), sticky="nsew")
        tk.Label(card, text=label, font=("Helvetica", 10), fg="#666666", bg="white").pack(anchor="w")
        tk.Label(card, text=value, font=("Helvetica", 18, "bold"), fg="#2E7D32", bg="white").pack(anchor="w")

    def refresh_data(self):
        try:
            headers = {"Authorization": f"Bearer {self.controller.token}"}
            response = requests.get(f"{self.controller.api_base_url}/accountant/accounts", headers=headers)
            if response.status_code == 200:
                accounts = response.json()
                for item in self.tree.get_children():
                    self.tree.delete(item)
                for acc in accounts:
                    self.tree.insert("", "end", values=(
                        acc['account_id'], acc['customer_name'], acc['account_type'], 
                        f"{acc['balance']:.2f}", acc['status']
                    ))
        except Exception as e:
            print(f"Error refreshing accountant data: {e}")
