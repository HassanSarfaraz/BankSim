-- ===========================================================================
-- SecureBank — Indexes for Query Optimization
-- Run EXPLAIN ANALYZE on queries to verify index usage.
-- ===========================================================================

-- Auth: fast username lookup
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Customer search by CNIC
CREATE INDEX IF NOT EXISTS idx_customers_cnic ON customers(cnic);

-- Transaction history per account (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_txn_from_account ON transactions(from_account);
CREATE INDEX IF NOT EXISTS idx_txn_to_account   ON transactions(to_account);

-- Transaction history sorted by date (range scans)
CREATE INDEX IF NOT EXISTS idx_txn_timestamp ON transactions(timestamp DESC);

-- Daily limit check: today's transactions for an account
CREATE INDEX IF NOT EXISTS idx_txn_date_from ON transactions(from_account, (DATE(timestamp)));

-- Account lookup by customer
CREATE INDEX IF NOT EXISTS idx_accounts_customer ON accounts(customer_id);

-- Card lookup by number
CREATE INDEX IF NOT EXISTS idx_cards_number ON cards(card_number);

-- Loan lookup by account
CREATE INDEX IF NOT EXISTS idx_loans_account ON loans(account_id);

-- Loan filter by status (pending, active, etc.)
CREATE INDEX IF NOT EXISTS idx_loans_status ON loans(status);
