# BankSim

A full-stack banking simulation platform built as a DBMS semester project. The system implements a production-grade PostgreSQL schema in Third Normal Form (3NF), a Python Flask backend, server-side session management, and bidirectional cloud synchronization with Google Firebase Firestore.

---

## Table of Contents

- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [Environment Variables](#environment-variables)
- [Default Credentials](#default-credentials)
- [Application Routes](#application-routes)
- [Database Design](#database-design)
- [Key Features](#key-features)
- [Known Limitations](#known-limitations)

---

## Architecture

```
Browser
  |
Flask Application (run.py)
  |-- Auth Routes      (/login, /logout, /signup)
  |-- Customer Routes  (/customer/*)
  |-- Admin Routes     (/admin/*)
  |
PostgreSQL (banksim)         Firebase Firestore
  |-- schema.sql               (cloud backup / restore)
  |-- triggers.sql
  |-- views.sql
  |-- functions_and_procedures.sql
```

On every write operation, the change is pushed to Firestore immediately. On application startup, missing records are pulled from Firestore into PostgreSQL. A manual full backup and restore is also available from the admin dashboard.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Web Framework | Flask 3.x (Python) |
| Database | PostgreSQL 15+ |
| Cloud Sync | Google Firebase Firestore |
| Sessions | Flask-Session (server-side, filesystem) |
| Password Hashing | bcrypt |
| Frontend | HTML5, Vanilla CSS (Glassmorphism design) |

---

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 15 or higher
- A Google Firebase project with Firestore (Native Mode) enabled
- `pip` and `venv`

---

## Project Structure

```
banksim/
|-- app/
|   |-- __init__.py           Application factory, DB view auto-recovery
|   |-- routes/
|   |   |-- auth.py           Login, logout, signup flow
|   |   |-- customer.py       Customer dashboard, transfer, deposit, support
|   |   |-- admin.py          Admin dashboard, approvals, fraud management
|   |-- models/
|   |   |-- db.py             PostgreSQL connection helper (per-request)
|   |-- backup/
|   |   |-- sync.py           Firebase bidirectional sync logic
|   |-- firebase/
|   |   |-- firestore.py      Firebase Admin SDK initialization
|   |-- templates/
|   |   |-- login.html
|   |   |-- signup.html
|   |   |-- dashboard/
|   |       |-- customer.html
|   |       |-- admin.html
|   |       |-- admin_customer_edit.html
|   |-- static/
|       |-- profile_pics/     Uploaded profile images
|-- sql/
|   |-- schema.sql            Table definitions (3NF)
|   |-- triggers.sql          All database triggers
|   |-- views.sql             All database views
|   |-- functions_and_procedures.sql  Stored procedures and functions
|   |-- seed_data.sql         Initial roles and sample users
|   |-- migration_patch_v1.sql  One-time data standardization script
|-- config.py                 App configuration loaded from environment
|-- run.py                    Application entry point
|-- requirements.txt
|-- .gitignore
|-- firebase-credentials.json  (gitignored — not in repo)
```

---

## Setup Instructions

### Step 1: Clone and Create Virtual Environment

```bash
git clone <repository-url>
cd banksim
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Linux/Mac
pip install -r requirements.txt
```

### Step 2: Configure PostgreSQL

Create a database named `banksim` in your PostgreSQL server, then execute the SQL files in this exact order using pgAdmin 4 or psql:

```sql
-- 1. Create all tables
\i sql/schema.sql

-- 2. Create triggers
\i sql/triggers.sql

-- 3. Create views
\i sql/views.sql

-- 4. Create stored procedures and functions
\i sql/functions_and_procedures.sql

-- 5. Insert seed data (roles and sample users)
\i sql/seed_data.sql
```

### Step 3: Configure Environment Variables

Create a `.env` file in the project root:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=banksim
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_CREDENTIALS=firebase-credentials.json
```

### Step 4: Configure Firebase

1. Go to the Firebase Console and create a project.
2. Enable Firestore Database in Native Mode.
3. Go to Project Settings > Service Accounts > Generate new private key.
4. Save the downloaded JSON as `firebase-credentials.json` in the project root.

### Step 5: Run the Application

```bash
python run.py
```

The application will start at `http://localhost:5000`.

On startup, the application automatically:
- Ensures all database views exist (recreates them if dropped)
- Ensures the `support_tickets` table exists
- Pulls any missing records from Firebase into PostgreSQL

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| POSTGRES_USER | postgres | PostgreSQL username |
| POSTGRES_PASSWORD | password | PostgreSQL password |
| POSTGRES_DB | banksim | Database name |
| POSTGRES_HOST | localhost | Database host |
| POSTGRES_PORT | 5432 | Database port |
| FIREBASE_PROJECT_ID | dbms-banksim | Firebase project ID |
| FIREBASE_CREDENTIALS | firebase-credentials.json | Path to service account key |

---

## Default Credentials

These accounts are created by `seed_data.sql` for testing purposes.

| Username | Password | Role |
|---|---|---|
| admin | admin123 | Administrator |
| hassan | customer123 | Customer |
| affan | affan123 | Customer |

---

## Application Routes

### Authentication

| Method | Route | Description |
|---|---|---|
| GET/POST | `/login` | Login page |
| GET | `/logout` | Logout and session clear |
| GET/POST | `/signup` | Submit new account request |

### Customer (`/customer/`)

| Method | Route | Description |
|---|---|---|
| GET | `/customer/dashboard` | Main dashboard |
| POST | `/customer/transfer` | Submit a fund transfer |
| POST | `/customer/request_deposit` | Request a cash deposit |
| POST | `/customer/open_account` | Request a new sub-account |
| POST | `/customer/upload-profile-pic` | Upload profile picture |
| POST | `/customer/upload-kyc` | Upload KYC document |
| POST | `/customer/submit_ticket` | Submit a support ticket |

### Admin (`/admin/`)

| Method | Route | Description |
|---|---|---|
| GET | `/admin/dashboard` | Admin control panel |
| POST | `/admin/handle_account_request/<id>/<action>` | Approve or reject new user |
| POST | `/admin/handle_pending_account/<id>/<action>` | Approve or reject sub-account |
| POST | `/admin/handle_deposit/<id>/<action>` | Approve or reject deposit |
| POST | `/admin/handle_fraud/<id>/<action>` | Approve or reject large transaction |
| POST | `/admin/resolve_ticket/<id>` | Reply to support ticket |
| POST | `/admin/toggle_lock/<user_id>` | Lock or unlock user account |
| GET/POST | `/admin/edit_customer/<id>` | Edit customer profile |
| POST | `/admin/undo_transaction/<id>` | Reverse a completed transaction |
| POST | `/admin/post-interest` | Post monthly interest to savings |
| POST | `/admin/backup/push` | Manual Postgres to Firebase backup |
| POST | `/admin/backup/pull` | Manual Firebase to Postgres restore |

---

## Database Design

### Tables

| Table | Purpose |
|---|---|
| roles | Customer, teller, admin, fraud_analyst roles |
| users | Login credentials, role assignment, last login tracking |
| customers | Personal profile data for customer-role users |
| accounts | Bank accounts linked to customers |
| transactions | Partitioned by year (2025/2026), all financial movements |
| loans | Loan records with EMI and maturity tracking |
| fraud_alerts | Auto-flagged records for large transactions |
| login_attempts | Login audit log used for auto-lockout |
| audit_log | Admin action history |
| media_storage | KYC documents stored as BYTEA |
| deposit_requests | Customer-initiated cash deposit requests |
| account_requests | New user signup requests awaiting admin approval |
| support_tickets | Customer support messages and admin replies |

### Triggers

| Trigger | Table | Effect |
|---|---|---|
| trg_login_lockout | login_attempts | Locks account after 5 failed logins in 15 minutes |
| trg_intercept_large_txn | transactions | Sets status to pending for amounts >= 10,000 |
| trg_balance_management | transactions | Updates account balance and sets balance_after snapshot |
| trg_flag_large_txn | transactions | Inserts fraud alert for amounts >= 10,000 |

### Views

| View | Used By |
|---|---|
| active_accounts_view | Admin dashboard, account listing |
| recent_audit_view | Admin dashboard, audit log section |
| overdue_loans_view | Admin (future use) |
| open_fraud_alerts_view | Available for reporting (SQL-level use) |

---

## Key Features

### Role-Based Access Control
- Three active roles: customer (1), teller (2), admin (3)
- All routes check session role before executing
- Customers can only access their own data

### Large Transaction Workflow
1. Customer initiates transfer of amount >= 10,000
2. Database trigger intercepts and sets status to pending
3. Fraud alert is created automatically
4. Admin reviews and approves or rejects
5. On approval, the balance trigger fires and updates accounts

### Auto-Lockout
After 5 failed login attempts within 15 minutes, the user account is automatically set to inactive. The admin can re-enable it via the dashboard.

### Cloud Sync Strategy
- Write-through: every DB change is immediately pushed to Firestore
- Read-on-login: missing records are pulled from Firestore on session start
- Full backup and restore available from admin dashboard
- Partitioned transaction tables are synced directly (not through parent)

---

## Known Limitations

- The `teller` role (role_id=2) is defined in the schema and in session checks but has no dedicated routes or dashboard yet. Tellers are redirected to the customer dashboard.
- Firebase Storage integration for profile pictures exists but file retrieval from cloud is not implemented. Files are served locally from `app/static/profile_pics/`.
- Transaction partitioning covers 2025 and 2026 only. Transactions outside this range will fail to insert until a new partition is added.
- The `generate_statement` stored procedure outputs via `RAISE NOTICE` (server log) and is not exposed through the UI.
