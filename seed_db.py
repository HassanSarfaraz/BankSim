#!/usr/bin/env python3
"""
SecureBank - Database Seeder Script
Populates the database with realistic sample data using bcrypt hashes.
Run from project root:  python seed_db.py
"""
import os, sys, bcrypt, psycopg2, random, string
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DB_URL",
    f"host={os.environ.get('DB_HOST','localhost')} "
    f"port={os.environ.get('DB_PORT','5432')} "
    f"dbname={os.environ.get('DB_NAME','securebank')} "
    f"user={os.environ.get('DB_USER','postgres')} "
    f"password={os.environ.get('DB_PASSWORD','postgres_password')}")

def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(12)).decode()

def rand_card() -> str:
    return ''.join(random.choices(string.digits, k=16))

def run():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        # ---- AUDIT POLICIES -------------------------------------------------
        cur.execute("INSERT INTO audit_policies (acc_type, daily_withdrawal_limit, overdraft_allowed, min_balance, interest_rate) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (acc_type) DO NOTHING",
            ('savings', 50000.00, False, 500.00, 5.50))
        cur.execute("INSERT INTO audit_policies (acc_type, daily_withdrawal_limit, overdraft_allowed, min_balance, interest_rate) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (acc_type) DO NOTHING",
            ('current', 200000.00, True, 0.00, 0.00))
        cur.execute("INSERT INTO audit_policies (acc_type, daily_withdrawal_limit, overdraft_allowed, min_balance, interest_rate) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (acc_type) DO NOTHING",
            ('fixed_deposit', 0.00, False, 10000.00, 9.00))

        # ---- BRANCHES -------------------------------------------------------
        cur.execute("INSERT INTO branches (name, city, address, phone) VALUES (%s,%s,%s,%s) RETURNING branch_id",
            ('Main Branch', 'Islamabad', 'Sector F-7 Markaz, Islamabad', '051-111-0001'))
        b1 = cur.fetchone()[0]
        cur.execute("INSERT INTO branches (name, city, address, phone) VALUES (%s,%s,%s,%s) RETURNING branch_id",
            ('Blue Area Branch', 'Islamabad', 'Jinnah Avenue, Blue Area', '051-111-0002'))
        b2 = cur.fetchone()[0]
        cur.execute("INSERT INTO branches (name, city, address, phone) VALUES (%s,%s,%s,%s) RETURNING branch_id",
            ('Gulberg Branch', 'Lahore', 'Main Blvd, Gulberg III, Lahore', '042-111-0003'))
        b3 = cur.fetchone()[0]

        # ---- MANAGER --------------------------------------------------------
        cur.execute("INSERT INTO users (username, password_hash, role) VALUES (%s,%s,%s) RETURNING user_id",
            ('manager1', hash_pw('Manager@123'), 'manager'))
        mgr_uid = cur.fetchone()[0]
        cur.execute("INSERT INTO employees (user_id, branch_id, full_name, designation) VALUES (%s,%s,%s,%s) RETURNING employee_id",
            (mgr_uid, b1, 'Ali Khan', 'Branch Manager'))
        mgr_eid = cur.fetchone()[0]

        # ---- ACCOUNTANT -----------------------------------------------------
        cur.execute("INSERT INTO users (username, password_hash, role) VALUES (%s,%s,%s) RETURNING user_id",
            ('accountant1', hash_pw('Acc@123'), 'accountant'))
        acc_uid = cur.fetchone()[0]
        cur.execute("INSERT INTO employees (user_id, branch_id, full_name, designation) VALUES (%s,%s,%s,%s)",
            (acc_uid, b1, 'Fatima Noor', 'Senior Accountant'))

        # ---- CUSTOMERS ------------------------------------------------------
        customers = [
            ('customer1', 'Cust@123', '37405-1234567-1', 'Muhammad Shahnawaz', date(1998,5,15), '0300-1234567', 'shahnawaz@example.com'),
            ('customer2', 'Cust@123', '37405-2345678-2', 'Ayesha Tariq',       date(1995,8,22), '0311-2345678', 'ayesha@example.com'),
            ('customer3', 'Cust@123', '37405-3456789-3', 'Usman Ghani',        date(2000,3,10), '0321-3456789', 'usman@example.com'),
            ('customer4', 'Cust@123', '37405-4567890-4', 'Zara Malik',         date(1993,11,5), '0333-4567890', 'zara@example.com'),
            ('customer5', 'Cust@123', '37405-5678901-5', 'Hassan Raza',        date(1990,7,19), '0345-5678901', 'hassan@example.com'),
        ]

        cust_accounts = []
        for uname, pw, cnic, name, dob, phone, email in customers:
            cur.execute("INSERT INTO users (username, password_hash, role) VALUES (%s,%s,%s) RETURNING user_id",
                (uname, hash_pw(pw), 'customer'))
            uid = cur.fetchone()[0]
            cur.execute("INSERT INTO customers (user_id, cnic, full_name, dob, phone, email, kyc_status) VALUES (%s,%s,%s,%s,%s,%s,'verified') RETURNING customer_id",
                (uid, cnic, name, dob, phone, email))
            cid = cur.fetchone()[0]
            cust_accounts.append((cid, uid))

        # ---- ACCOUNTS -------------------------------------------------------
        branches_list = [b1, b2, b3]
        account_ids = []
        for i, (cid, uid) in enumerate(cust_accounts):
            branch = branches_list[i % 3]
            # Savings account
            cur.execute("INSERT INTO accounts (customer_id, branch_id, type, balance, daily_limit) VALUES (%s,%s,'savings',%s,50000) RETURNING account_id",
                (cid, branch, round(random.uniform(5000, 200000), 2)))
            aid1 = cur.fetchone()[0]
            account_ids.append(aid1)
            # Current account for first two customers
            if i < 2:
                cur.execute("INSERT INTO accounts (customer_id, branch_id, type, balance, daily_limit) VALUES (%s,%s,'current',%s,200000) RETURNING account_id",
                    (cid, branch, round(random.uniform(50000, 500000), 2)))
                account_ids.append(cur.fetchone()[0])

        # ---- DEPOSIT TRANSACTIONS (initial) ---------------------------------
        sys_user = mgr_uid  # manager does the seeding
        for aid in account_ids:
            cur.execute("SELECT balance FROM accounts WHERE account_id = %s", (aid,))
            bal = cur.fetchone()[0]
            cur.execute("INSERT INTO transactions (to_account, amount, txn_type, status, description, performed_by) VALUES (%s,%s,'deposit','completed','Initial deposit',%s)",
                (aid, bal, sys_user))

        # ---- LOAN (sample) --------------------------------------------------
        cur.execute("INSERT INTO loans (account_id, loan_type, amount, interest_rate, term_months, monthly_payment, status, approved_by, approval_date) VALUES (%s,'personal',250000,12,24,12500,'active',%s,NOW())",
            (account_ids[0], mgr_eid))

        # ---- DEBIT CARDS ----------------------------------------------------
        for aid in account_ids[:3]:
            cur.execute("INSERT INTO cards (account_id, card_number, card_type, expiry_date, cvv_hash) VALUES (%s,%s,'debit',%s,%s)",
                (aid, rand_card(), date.today() + timedelta(days=1460), hash_pw('123')))

        conn.commit()
        print("✅ Database seeded successfully!")
    except Exception as e:
        conn.rollback()
        print(f"❌ Seeding failed: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    run()
