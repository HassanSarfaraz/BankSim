-- ===========================================================================
-- SecureBank Management System - PostgreSQL Schema
-- CS232 | GIK Institute | Prof. Muhammad Qasim Riaz
-- All tables are in BCNF. See db/normalization.md for proof.
-- ===========================================================================

-- Clean slate (order matters due to FK constraints)
DROP TABLE IF EXISTS cards, loans, transactions, accounts,
    employees, customers, branches, users, audit_policies CASCADE;
DROP TYPE IF EXISTS user_role, account_type, txn_status, loan_status, card_status CASCADE;

-- ---- ENUM TYPES -----------------------------------------------------------
CREATE TYPE user_role      AS ENUM ('manager', 'accountant', 'customer');
CREATE TYPE account_type   AS ENUM ('savings', 'current', 'fixed_deposit');
CREATE TYPE txn_status     AS ENUM ('pending', 'completed', 'failed', 'reversed');
CREATE TYPE loan_status    AS ENUM ('pending', 'approved', 'rejected', 'active', 'paid', 'defaulted');
CREATE TYPE card_status    AS ENUM ('active', 'blocked', 'expired');

-- ---- USERS ----------------------------------------------------------------
CREATE TABLE users (
    user_id       SERIAL PRIMARY KEY,
    username      VARCHAR(50)  UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          user_role    NOT NULL,
    is_active     BOOLEAN      DEFAULT TRUE,
    last_login    TIMESTAMP WITH TIME ZONE,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ---- BRANCHES -------------------------------------------------------------
CREATE TABLE branches (
    branch_id  SERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    city       VARCHAR(50)  NOT NULL,
    address    TEXT         NOT NULL,
    phone      VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ---- CUSTOMERS ------------------------------------------------------------
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    user_id     INTEGER UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    cnic        VARCHAR(15) UNIQUE NOT NULL,
    full_name   VARCHAR(100) NOT NULL,
    dob         DATE NOT NULL,
    address     TEXT,
    phone       VARCHAR(20),
    email       VARCHAR(100) UNIQUE,
    kyc_status  VARCHAR(20) DEFAULT 'pending',   -- pending, verified, rejected
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ---- EMPLOYEES ------------------------------------------------------------
CREATE TABLE employees (
    employee_id  SERIAL PRIMARY KEY,
    user_id      INTEGER UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    branch_id    INTEGER REFERENCES branches(branch_id),
    full_name    VARCHAR(100) NOT NULL,
    designation  VARCHAR(50)  NOT NULL,           -- e.g. Senior Accountant
    is_active    BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ---- AUDIT POLICIES (per account type) ------------------------------------
CREATE TABLE audit_policies (
    policy_id              SERIAL PRIMARY KEY,
    acc_type               account_type UNIQUE NOT NULL,
    daily_withdrawal_limit DECIMAL(15,2) NOT NULL,
    overdraft_allowed      BOOLEAN       DEFAULT FALSE,
    min_balance            DECIMAL(15,2) DEFAULT 0.00,
    interest_rate          DECIMAL(5,2)  DEFAULT 0.00
);

-- ---- ACCOUNTS -------------------------------------------------------------
CREATE TABLE accounts (
    account_id  SERIAL PRIMARY KEY,
    customer_id INTEGER      REFERENCES customers(customer_id) ON DELETE CASCADE,
    branch_id   INTEGER      REFERENCES branches(branch_id),
    type        account_type NOT NULL,
    balance     DECIMAL(15,2) DEFAULT 0.00 CHECK (balance >= 0),
    status      VARCHAR(20)   DEFAULT 'active',  -- active, frozen, closed
    daily_limit DECIMAL(15,2) DEFAULT 50000.00,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ---- TRANSACTIONS ---------------------------------------------------------
CREATE TABLE transactions (
    txn_id       SERIAL PRIMARY KEY,
    from_account INTEGER  REFERENCES accounts(account_id),
    to_account   INTEGER  REFERENCES accounts(account_id),
    amount       DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    txn_type     VARCHAR(30) NOT NULL,  -- transfer, deposit, withdrawal, loan_disbursement, loan_repayment
    status       txn_status  DEFAULT 'pending',
    description  TEXT,
    performed_by INTEGER REFERENCES users(user_id),
    timestamp    TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ---- LOANS ----------------------------------------------------------------
CREATE TABLE loans (
    loan_id        SERIAL PRIMARY KEY,
    account_id     INTEGER      REFERENCES accounts(account_id) ON DELETE CASCADE,
    loan_type      VARCHAR(20)  NOT NULL,   -- personal, home, auto
    amount         DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    interest_rate  DECIMAL(5,2)  NOT NULL,
    term_months    INTEGER       NOT NULL,
    monthly_payment DECIMAL(15,2),
    amount_paid    DECIMAL(15,2) DEFAULT 0.00,
    status         loan_status   DEFAULT 'pending',
    approved_by    INTEGER REFERENCES employees(employee_id),
    approval_date  TIMESTAMP WITH TIME ZONE,
    reason         TEXT,
    created_at     TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ---- CARDS ----------------------------------------------------------------
CREATE TABLE cards (
    card_id     SERIAL PRIMARY KEY,
    account_id  INTEGER    REFERENCES accounts(account_id) ON DELETE CASCADE,
    card_number VARCHAR(16) UNIQUE NOT NULL,
    card_type   VARCHAR(10) NOT NULL,  -- debit, credit
    expiry_date DATE        NOT NULL,
    cvv_hash    VARCHAR(255) NOT NULL,
    status      card_status  DEFAULT 'active',
    credit_limit DECIMAL(15,2) DEFAULT 0.00,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ===========================================================================
-- COMMENTS for documentation
-- ===========================================================================
COMMENT ON TABLE users       IS 'System login accounts. Roles: manager, accountant, customer.';
COMMENT ON TABLE customers   IS 'Customer personal data. 1-to-1 with users.';
COMMENT ON TABLE employees   IS 'Staff records. 1-to-1 with users.';
COMMENT ON TABLE branches    IS 'Bank branch locations.';
COMMENT ON TABLE accounts    IS 'Bank accounts linked to customers and branches.';
COMMENT ON TABLE transactions IS 'All monetary movements. Immutable audit trail.';
COMMENT ON TABLE loans       IS 'Loan applications and repayment tracking.';
COMMENT ON TABLE cards       IS 'Debit/credit cards issued per account.';
COMMENT ON TABLE audit_policies IS 'Per-account-type rules: limits, overdraft, rates.';
