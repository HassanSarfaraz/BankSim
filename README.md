# SecureBank Management System

> CS232 — Database Management System | GIK Institute | Prof. Muhammad Qasim Riaz

A full-stack banking application with **3 role-based Tkinter GUIs**, a **Flask REST API**, **PostgreSQL** for relational data, and **MongoDB** for audit logs.

---

## Prerequisites

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11+ | Backend + Frontend |
| PostgreSQL | 15+ | Relational database |
| MongoDB | 6+ | Audit logs, documents |

---

## Quick Start

### 1. Clone & Configure
```bash
git clone https://github.com/your-team/securebank.git
cd securebank
copy .env.example .env
# Edit .env with your PostgreSQL password
```

### 2. Create the Database
Open `psql` and run:
```sql
CREATE DATABASE securebank;
\c securebank
\i db/schema.sql
\i db/stored_procedures.sql
\i db/triggers.sql
\i db/views.sql
\i db/indexes.sql
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-gui.txt
```

### 4. Seed Sample Data
```bash
python seed_db.py
```

### 5. Start the Backend API
```bash
python -m backend.app
```

### 6. Launch the GUI (in a new terminal)
```bash
python -m frontend.main
```

---

## Default Credentials

| Role | Username | Password |
|------|----------|----------|
| Manager | `manager1` | `Manager@123` |
| Accountant | `accountant1` | `Acc@123` |
| Customer | `customer1` — `customer5` | `Cust@123` |

---

## Project Structure

```
securebank/
├── backend/                 # Flask REST API
│   ├── app.py               # App factory
│   ├── config.py            # Environment config
│   ├── extensions.py        # SQLAlchemy & JWT init
│   ├── models/              # ORM models (User, Account, Transaction, Loan, Card)
│   ├── routes/              # Blueprints: auth, manager, accountant, customer
│   ├── services/            # Business logic (transfer, deposit, withdrawal)
│   └── mongo/               # MongoDB audit logging
├── frontend/                # Tkinter GUI
│   ├── main.py              # Login screen & role router
│   ├── styles.py            # Design system (colors, fonts)
│   ├── utils/               # API client, dashboard base class
│   ├── manager/             # Manager dashboard (navy theme)
│   ├── accountant/          # Accountant dashboard (green theme)
│   └── customer/            # Customer dashboard (indigo theme)
├── db/                      # SQL scripts
│   ├── schema.sql           # DDL: tables, types, constraints
│   ├── stored_procedures.sql # sp_transfer, sp_deposit, sp_withdrawal
│   ├── triggers.sql         # Balance validation triggers
│   ├── views.sql            # Reporting views
│   ├── indexes.sql          # Performance indexes
│   └── normalization.md     # BCNF proof for all tables
├── seed_db.py               # Python seeder (bcrypt hashes)
├── requirements.txt         # Backend dependencies
├── requirements-gui.txt     # Frontend dependencies
└── .env.example             # Environment template
```

---

## Key CS232 Features

| Topic | Implementation | File |
|-------|---------------|------|
| ER Modeling | 9 entities with PK/FK relationships | `db/schema.sql` |
| Normalization | All tables in BCNF with proof | `db/normalization.md` |
| Transactions & ACID | Stored procedures with BEGIN/COMMIT | `db/stored_procedures.sql` |
| Concurrency Control | SELECT FOR UPDATE (row-level locking) | `db/stored_procedures.sql` |
| Triggers | Balance validation trigger | `db/triggers.sql` |
| Views | Account summary, branch performance | `db/views.sql` |
| Indexes | B-tree on timestamp, account_id, CNIC | `db/indexes.sql` |
| NoSQL | MongoDB audit logs, async writes | `backend/mongo/audit.py` |
| Role-Based Access | 3 separate Tkinter dashboards + JWT | `frontend/`, `backend/routes/` |

---

## API Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/api/auth/login` | Login, get JWT | Public |
| GET | `/api/manager/dashboard` | KPI metrics | Manager |
| POST | `/api/manager/employees` | Create employee | Manager |
| PUT | `/api/manager/loans/<id>/decide` | Approve/reject loan | Manager |
| GET | `/api/accountant/accounts` | List all accounts | Staff |
| POST | `/api/accountant/transactions/deposit` | Cash deposit | Staff |
| POST | `/api/accountant/transactions/transfer` | Fund transfer | Staff |
| GET | `/api/customer/accounts` | My accounts | Customer |
| POST | `/api/customer/transfer` | Self-service transfer | Customer |
| POST | `/api/customer/loans/apply` | Apply for loan | Customer |
