import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
from frontend.customer.dashboard import CustomerDashboard
from frontend.accountant.dashboard import AccountantDashboard
from frontend.manager.dashboard import ManagerDashboard
# (Other dashboard imports will follow as implemented)

# Themes and Colors
THEMES = {
    "login": {"bg": "#F5F7FA", "primary": "#1B3A6B", "text": "#333333"},
    "manager": {"bg": "#1B3A6B", "sidebar": "#152C52", "accent": "#FFD700", "text": "#FFFFFF"},
    "accountant": {"bg": "#F0F4F0", "sidebar": "#2E7D32", "accent": "#009688", "text": "#333333"},
    "customer": {"bg": "#FFFFFF", "sidebar": "#4A148C", "accent": "#00695C", "text": "#333333"}
}

API_BASE_URL = "http://localhost:5000/api"

class SecureBankApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SecureBank Management System")
        self.geometry("1000x700")
        self.configure(bg=THEMES["login"]["bg"])
        
        self.token = None
        self.user_role = None
        self.user_data = None

        self.container = tk.Frame(self, bg=THEMES["login"]["bg"])
        self.container.pack(fill="both", expand=True)

        self.show_login()

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_login(self):
        self.clear_container()
        login_frame = tk.Frame(self.container, bg="white", padx=40, pady=40, highlightbackground="#E1E4E8", highlightthickness=1)
        login_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(login_frame, text="SecureBank", font=("Helvetica", 28, "bold"), fg=THEMES["login"]["primary"], bg="white").pack(pady=(0, 10))
        tk.Label(login_frame, text="Enter your credentials to continue", font=("Helvetica", 10), fg="#666666", bg="white").pack(pady=(0, 30))

        tk.Label(login_frame, text="Username", font=("Helvetica", 10, "bold"), bg="white", fg="#333333").pack(anchor="w")
        self.username_entry = ttk.Entry(login_frame, width=35)
        self.username_entry.pack(pady=(5, 15))

        tk.Label(login_frame, text="Password", font=("Helvetica", 10, "bold"), bg="white", fg="#333333").pack(anchor="w")
        self.password_entry = ttk.Entry(login_frame, width=35, show="*")
        self.password_entry.pack(pady=(5, 30))

        login_btn = tk.Button(login_frame, text="Login", command=self.handle_login, 
                              bg=THEMES["login"]["primary"], fg="white", font=("Helvetica", 12, "bold"), 
                              width=20, pady=10, cursor="hand2", relief="flat")
        login_btn.pack()

    def handle_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        try:
            response = requests.post(f"{API_BASE_URL}/auth/login", json={
                "username": username,
                "password": password
            })
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["token"]
                self.user_role = data["role"]
                self.user_data = data["user"]
                self.load_dashboard()
            else:
                error_msg = response.json().get("error", "Login failed")
                messagebox.showerror("Login Error", error_msg)
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to server: {str(e)}")

    def load_dashboard(self):
        self.clear_container()
        if self.user_role == "manager":
            self.show_manager_dashboard()
        elif self.user_role == "accountant":
            self.show_accountant_dashboard()
        elif self.user_role == "customer":
            self.show_customer_dashboard()

    def show_manager_dashboard(self):
        self.clear_container()
        self.api_base_url = API_BASE_URL
        dashboard = ManagerDashboard(self.container, self)
        dashboard.pack(fill="both", expand=True)

    def show_accountant_dashboard(self):
        self.clear_container()
        self.api_base_url = API_BASE_URL
        dashboard = AccountantDashboard(self.container, self)
        dashboard.pack(fill="both", expand=True)

    def show_customer_dashboard(self):
        self.clear_container()
        self.api_base_url = API_BASE_URL # Pass down to components
        dashboard = CustomerDashboard(self.container, self)
        dashboard.pack(fill="both", expand=True)

if __name__ == "__main__":
    app = SecureBankApp()
    app.mainloop()
