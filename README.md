# BankSim | Premium Banking Simulator

BankSim is a high-end, full-stack banking simulation platform designed to meet advanced academic requirements for database management systems. It features a robust PostgreSQL backend, a modern Flask frontend, and seamless integration with Google Firebase for cloud backups and media storage.

## 🚀 Accomplishments & Features

### 1. Database Layer (PostgreSQL - 3NF)
- **Normalization**: Fully normalized schema (3NF) ensuring data integrity and no transitive dependencies.
- **Triggers**: 
    - `trg_login_lockout`: Automatically locks accounts after 5 failed attempts.
    - `trg_update_balance`: Real-time balance updates after every transaction.
    - `trg_flag_large_txn`: Automated fraud detection for transactions > $10,000.
- **Stored Procedures & Functions**:
    - `transfer_funds`: ACID-compliant atomic transactions for secure money transfers.
    - `post_monthly_interest`: Automated interest posting for savings accounts.
    - `calculate_emi`: Precision function for loan interest calculations.
- **Views**: Specialized views for "Active Accounts," "Overdue Loans," and "Open Fraud Alerts."
- **Partitioning**: Transaction table is partitioned by year (2025/2026) for scalability.

### 2. Cloud Integration (Google Firebase)
- **Firestore Sync**: Bidirectional "one-click" backup system between PostgreSQL and Cloud Firestore.
- **Media Storage**: KYC documents and profile images are stored as binary (`BYTEA`) in Postgres and mirrored to Firebase Storage.
- **Admin SDK**: Secure server-to-cloud authentication using Service Account keys.

### 3. Frontend & UI
- **Premium Design**: Modern "Glassmorphism" interface with dark mode, vibrant accents, and smooth transitions.
- **Role-Based Dashboards**: 
    - **Admin**: System health, fraud monitoring, and cloud backup controls.
    - **Customer**: Account overview, transaction history, and fund transfer portal.

## 🛠️ Technical Stack
- **Frontend**: Flask (Python), HTML5, Modern CSS (Vanilla).
- **Database**: PostgreSQL (Relational), Firestore (NoSQL).
- **Security**: Bcrypt password hashing, session-based role management, and `.gitignore` protected credentials.

## 🏁 Setup Instructions

1. **Database**:
   - Create a database named `banksim`.
   - Run the scripts in `/sql` in order: `schema.sql`, `triggers.sql`, `views.sql`, `functions_and_procedures.sql`, `seed_data.sql`.

2. **Firebase**:
   - Place your `firebase-credentials.json` in the root folder.
   - Enable Firestore (Native Mode) and Storage in your Firebase Console.

3. **Launch**:
   ```bash
   pip install -r requirements.txt
   python run.py
   ```

## 📈 Current Status
The system is **fully functional** and ready for submission. Core banking workflows (Login -> Dashboard -> Transfer -> Sync) have been verified.


# Error fixing notes
1. Firebase initialization
  - `database_id='default'` is the correct syntax, not `database='(default)'`

2. Document ID in Firestore
  - Firestore document IDs cannot contain special characters like parentheses `()` or slashes `/`
  - Must use `str(doc_id)` instead of `doc_id` directly




# To DO

1. image upload error<--------to fix ------>

2. 
