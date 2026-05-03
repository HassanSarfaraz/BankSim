import tkinter as tk
from tkinter import ttk, messagebox
import requests
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

class ManagerDashboard(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg="#F5F7FA")
        
        self.setup_ui()

    def setup_ui(self):
        # Sidebar
        sidebar = tk.Frame(self, bg="#1B3A6B", width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="SecureBank Admin", fg="white", bg="#1B3A6B", font=("Helvetica", 14, "bold")).pack(pady=30)

        menu_items = [
            ("Dashboard", self.show_stats),
            ("Employees", None),
            ("Branches", None),
            ("Audit Logs", self.show_audit_logs),
            ("Reports", None)
        ]

        for text, command in menu_items:
            tk.Button(sidebar, text=text, bg="#1B3A6B", fg="white", relief="flat", 
                      padx=20, pady=12, anchor="w", cursor="hand2", command=command).pack(fill="x")

        tk.Button(sidebar, text="Logout", command=self.controller.show_login, 
                  bg="#152C52", fg="white", relief="flat", pady=15).pack(side="bottom", fill="x")

        # Main Content
        self.main_area = tk.Frame(self, bg="#F5F7FA", padx=30, pady=30)
        self.main_area.pack(side="right", fill="both", expand=True)

        self.show_stats()

    def show_stats(self):
        for widget in self.main_area.winfo_children():
            widget.destroy()

        tk.Label(self.main_area, text="Executive Overview", font=("Helvetica", 22, "bold"), bg="#F5F7FA", fg="#1B3A6B").pack(anchor="w")
        
        # KPI Cards
        kpi_frame = tk.Frame(self.main_area, bg="#F5F7FA")
        kpi_frame.pack(fill="x", pady=20)

        self.create_kpi_card(kpi_frame, "Total Assets", "PKR 54.2M", 0)
        self.create_kpi_card(kpi_frame, "Total Customers", "1,850", 1)
        self.create_kpi_card(kpi_frame, "Active Branches", "3", 2)

        # Chart Section
        chart_frame = tk.Frame(self.main_area, bg="white", padx=20, pady=20, highlightbackground="#E1E4E8", highlightthickness=1)
        chart_frame.pack(fill="both", expand=True, pady=20)
        
        tk.Label(chart_frame, text="Transaction Volume (Last 7 Days)", font=("Helvetica", 12, "bold"), bg="white").pack(anchor="w")
        
        # Embed Matplotlib Chart
        fig = Figure(figsize=(5, 3), dpi=100)
        ax = fig.add_subplot(111)
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        volumes = [120, 150, 110, 180, 210, 90, 80]
        ax.bar(days, volumes, color='#1B3A6B')
        ax.set_facecolor('#F5F7FA')
        fig.patch.set_facecolor('white')
        
        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def create_kpi_card(self, parent, label, value, col):
        card = tk.Frame(parent, bg="white", padx=20, pady=20, highlightbackground="#E1E4E8", highlightthickness=1)
        card.grid(row=0, column=col, padx=(0, 20), sticky="nsew")
        tk.Label(card, text=label, font=("Helvetica", 10), fg="#666666", bg="white").pack(anchor="w")
        tk.Label(card, text=value, font=("Helvetica", 18, "bold"), fg="#1B3A6B", bg="white").pack(anchor="w")

    def show_audit_logs(self):
        for widget in self.main_area.winfo_children():
            widget.destroy()

        tk.Label(self.main_area, text="System Audit Logs (MongoDB)", font=("Helvetica", 18, "bold"), bg="#F5F7FA").pack(anchor="w", pady=(0, 20))
        
        columns = ("Time", "User ID", "Action", "Status", "IP")
        tree = ttk.Treeview(self.main_area, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)
        
        tree.pack(fill="both", expand=True)

        try:
            headers = {"Authorization": f"Bearer {self.controller.token}"}
            response = requests.get(f"{self.controller.api_base_url}/manager/audit-logs", headers=headers)
            if response.status_code == 200:
                logs = response.json()
                for log in logs:
                    tree.insert("", "end", values=(
                        log['timestamp'][:19].replace('T', ' '),
                        log.get('user_id', 'N/A'),
                        log['action'],
                        log['status'],
                        log.get('ip_address', 'Unknown')
                    ))
        except Exception as e:
            print(f"Error loading audit logs: {e}")
