-- schema.sql
-- 1. ROLES
CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL
);

-- 2. USERS
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role_id INT REFERENCES roles(role_id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    profile_image BYTEA
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role_id);

-- 3. CUSTOMERS (3NF - Separate from users)
CREATE TABLE customers (
    customer_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    phone VARCHAR(20),
    city VARCHAR(100),
    country VARCHAR(100),
    kyc_status VARCHAR(20) DEFAULT 'pending',
    credit_score INT DEFAULT 600,
    customer_since DATE DEFAULT CURRENT_DATE
);

-- 4. ACCOUNTS
CREATE TABLE accounts (
    account_id BIGSERIAL PRIMARY KEY,
    account_number VARCHAR(20) UNIQUE NOT NULL,
    customer_id BIGINT REFERENCES customers(customer_id),
    account_type VARCHAR(20) CHECK (account_type IN ('checking','savings','credit','loan')),
    balance DECIMAL(15,2) DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) DEFAULT 'active',
    interest_rate DECIMAL(5,4) DEFAULT 0.0300,
    minimum_balance DECIMAL(10,2) DEFAULT 0.00,
    overdraft_limit DECIMAL(10,2) DEFAULT 0.00,
    opened_date DATE DEFAULT CURRENT_DATE
);
CREATE INDEX idx_accounts_customer ON accounts(customer_id);

-- 5. TRANSACTIONS (Partitioned)
CREATE TABLE transactions (
    transaction_id BIGSERIAL,
    account_id BIGINT REFERENCES accounts(account_id),
    transaction_type VARCHAR(20) CHECK (transaction_type IN ('deposit','withdrawal','transfer','payment','fee')),
    amount DECIMAL(15,2) NOT NULL,
    balance_after DECIMAL(15,2),
    description TEXT,
    reference_number VARCHAR(50),
    status VARCHAR(20) DEFAULT 'completed',
    transaction_date TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (transaction_date);

CREATE TABLE transactions_2025 PARTITION OF transactions
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE transactions_2026 PARTITION OF transactions
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

CREATE INDEX idx_txn_account_date ON transactions(account_id, transaction_date DESC);

-- 6. LOANS
CREATE TABLE loans (
    loan_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT REFERENCES customers(customer_id),
    loan_type VARCHAR(30),
    principal_amount DECIMAL(15,2),
    interest_rate DECIMAL(5,4),
    tenure_months INT,
    emi DECIMAL(10,2),
    outstanding_balance DECIMAL(15,2),
    status VARCHAR(20) DEFAULT 'pending',
    disbursement_date DATE,
    maturity_date DATE
);

-- 7. FRAUD ALERTS
CREATE TABLE fraud_alerts (
    alert_id BIGSERIAL PRIMARY KEY,
    transaction_id BIGINT,
    account_id BIGINT REFERENCES accounts(account_id),
    alert_type VARCHAR(50),
    severity VARCHAR(20) CHECK (severity IN ('low','medium','high','critical')),
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 8. LOGIN ATTEMPTS
CREATE TABLE login_attempts (
    attempt_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    attempt_time TIMESTAMP DEFAULT NOW(),
    success BOOLEAN,
    ip_address VARCHAR(45)
);

-- 9. AUDIT LOG
CREATE TABLE audit_log (
    log_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    action VARCHAR(100),
    table_name VARCHAR(50),
    record_id BIGINT,
    old_value JSONB,
    new_value JSONB,
    log_time TIMESTAMP DEFAULT NOW()
);

-- 10. MEDIA STORAGE
CREATE TABLE media_storage (
    media_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    media_type VARCHAR(20) CHECK (media_type IN ('image','audio','video','document')),
    file_name VARCHAR(255),
    file_data BYTEA,
    firebase_path VARCHAR(500),
    uploaded_at TIMESTAMP DEFAULT NOW()
);

-- 11. DEPOSIT REQUESTS
CREATE TABLE deposit_requests (
    request_id BIGSERIAL PRIMARY KEY,
    account_id BIGINT REFERENCES accounts(account_id),
    amount DECIMAL(15,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 12. ACCOUNT REQUESTS
CREATE TABLE account_requests (
    request_id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);
