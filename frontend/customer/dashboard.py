import tkinter as tk
from tkinter import ttk, messagebox
import requests

class CustomerDashboard(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg="white")
        
        self.setup_ui()

    def setup_ui(self):
        # Header
        header = tk.Frame(self, bg="#4A148C", height=60)
        header.pack(fill="x")
        tk.Label(header, text=f"Welcome, {self.controller.user_data['username']}", 
                 fg="white", bg="#4A148C", font=("Helvetica", 14, "bold")).pack(side="left", padx=20)
        
        tk.Button(header, text="Logout", command=self.controller.show_login, 
                  bg="#7B1FA2", fg="white", relief="flat").pack(side="right", padx=20, pady=15)

        # Main Content
        content = tk.Frame(self, bg="white", padx=30, pady=20)
        content.pack(fill="both", expand=True)

        # Account Cards Container
        tk.Label(content, text="My Accounts", font=("Helvetica", 18, "bold"), bg="white").pack(anchor="w", pady=(0, 20))
        
        self.accounts_frame = tk.Frame(content, bg="white")
        self.accounts_frame.pack(fill="x")
        
        self.refresh_accounts()

        # Transfer Section
        tk.Label(content, text="Quick Transfer", font=("Helvetica", 16, "bold"), bg="white").pack(anchor="w", pady=(30, 10))
        transfer_card = tk.Frame(content, bg="#F3E5F5", padx=20, pady=20)
        transfer_card.pack(fill="x")

        tk.Label(transfer_card, text="Recipient Account ID", bg="#F3E5F5").grid(row=0, column=0, sticky="w")
        self.to_acc_entry = ttk.Entry(transfer_card)
        self.to_acc_entry.grid(row=1, column=0, padx=(0, 20), pady=5)

        tk.Label(transfer_card, text="Amount (PKR)", bg="#F3E5F5").grid(row=0, column=1, sticky="w")
        self.amount_entry = ttk.Entry(transfer_card)
        self.amount_entry.grid(row=1, column=1, padx=(0, 20), pady=5)

        tk.Button(transfer_card, text="Send Money", command=self.handle_transfer,
                  bg="#00695C", fg="white", font=("Helvetica", 10, "bold"), padx=20).grid(row=1, column=2)

    def refresh_accounts(self):
        # Clear existing cards
        for widget in self.accounts_frame.winfo_children():
            widget.destroy()

        try:
            headers = {"Authorization": f"Bearer {self.controller.token}"}
            response = requests.get(f"{self.controller.api_base_url}/customer/accounts", headers=headers)
            if response.status_code == 200:
                accounts = response.json()
                for i, acc in enumerate(accounts):
                    card = tk.Frame(self.accounts_frame, bg="#FFFFFF", highlightbackground="#E0E0E0", 
                                    highlightthickness=1, padx=20, pady=20)
                    card.grid(row=0, column=i, padx=10, sticky="nsew")
                    
                    tk.Label(card, text=acc['account_type'].upper(), font=("Helvetica", 10, "bold"), fg="#666666", bg="white").pack(anchor="w")
                    tk.Label(card, text=f"PKR {acc['balance']:,.2f}", font=("Helvetica", 20, "bold"), fg="#4A148C", bg="white").pack(anchor="w", pady=5)
                    tk.Label(card, text=f"Account: {acc['account_id']}", font=("Helvetica", 9), fg="#999999", bg="white").pack(anchor="w")
            else:
                messagebox.showerror("Error", "Failed to load accounts")
        except Exception as e:
            print(f"Error refreshing accounts: {e}")

    def handle_transfer(self):
        to_acc = self.to_acc_entry.get()
        amount = self.amount_entry.get()
        
        # Simple validation
        if not to_acc or not amount:
            messagebox.showwarning("Warning", "Please fill all fields")
            return

        try:
            headers = {"Authorization": f"Bearer {self.controller.token}"}
            # For simplicity, we'll use the first account as source for now
            # In a real UI, the user would select which account to transfer from
            response = requests.get(f"{self.controller.api_base_url}/customer/accounts", headers=headers)
            from_acc = response.json()[0]['account_id']

            response = requests.post(f"{self.controller.api_base_url}/customer/transfer", headers=headers, json={
                "from_account": from_acc,
                "to_account": int(to_acc),
                "amount": float(amount)
            })

            if response.status_code == 200:
                messagebox.showinfo("Success", "Transfer completed successfully!")
                self.refresh_accounts()
                self.to_acc_entry.delete(0, tk.END)
                self.amount_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Error", response.json().get("error", "Transfer failed"))
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
