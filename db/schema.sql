-- CS232 - Database Management System
-- Project: SecureBank Management System
-- Schema Definition

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Branches Table
CREATE TABLE branches (
    branch_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Users Table (Core Auth)
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('manager', 'accountant', 'customer')),
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Customers Table
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    cnic VARCHAR(15) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    dob DATE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    address TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Employees Table
CREATE TABLE employees (
    employee_id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    branch_id INTEGER REFERENCES branches(branch_id),
    role VARCHAR(50) NOT NULL,
    salary DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    hire_date DATE DEFAULT CURRENT_DATE
);

-- 5. Accounts Table
CREATE TABLE accounts (
    account_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    branch_id INTEGER REFERENCES branches(branch_id),
    account_type VARCHAR(20) NOT NULL CHECK (account_type IN ('savings', 'current', 'fixed_deposit')),
    balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00 CHECK (balance >= 0),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'frozen')),
    currency VARCHAR(3) DEFAULT 'PKR',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Transactions Table
CREATE TABLE transactions (
    txn_id SERIAL PRIMARY KEY,
    from_account INTEGER REFERENCES accounts(account_id),
    to_account INTEGER REFERENCES accounts(account_id),
    amount DECIMAL(15, 2) NOT NULL CHECK (amount > 0),
    txn_type VARCHAR(20) NOT NULL CHECK (txn_type IN ('deposit', 'withdrawal', 'transfer', 'loan_disbursement', 'loan_repayment')),
    status VARCHAR(20) DEFAULT 'completed' CHECK (status IN ('pending', 'completed', 'failed')),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Loans Table
CREATE TABLE loans (
    loan_id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(account_id),
    loan_type VARCHAR(50) NOT NULL, -- personal, home, auto
    principal_amount DECIMAL(15, 2) NOT NULL,
    interest_rate DECIMAL(5, 2) NOT NULL,
    term_months INTEGER NOT NULL,
    remaining_balance DECIMAL(15, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'active', 'paid', 'defaulted')),
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP WITH TIME ZONE
);

-- 8. Cards Table
CREATE TABLE cards (
    card_id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(account_id),
    card_number VARCHAR(16) UNIQUE NOT NULL,
    card_type VARCHAR(20) NOT NULL CHECK (card_type IN ('debit', 'credit')),
    expiry_date DATE NOT NULL,
    cvv VARCHAR(4) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'blocked', 'expired')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
