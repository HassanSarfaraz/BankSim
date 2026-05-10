-- =============================================================================
-- BankSim: Consolidated Patch (All Scratch Fixes)
-- Run this in pgAdmin Query Tool to apply all pending fixes to your database.
-- Safe to re-run — all statements use IF NOT EXISTS / OR REPLACE / ON CONFLICT.
-- =============================================================================

-- ─────────────────────────────────────────────────────────────
-- 1. SCHEMA FIXES
-- ─────────────────────────────────────────────────────────────

-- 1a. Ensure profile_image column is VARCHAR(255) (not BYTEA)
ALTER TABLE users ALTER COLUMN profile_image TYPE VARCHAR(255) USING NULL;

-- 1b. Ensure previous_login column exists on users
ALTER TABLE users ADD COLUMN IF NOT EXISTS previous_login TIMESTAMP;

-- 1c. Fix account_type constraint to include 'business'
ALTER TABLE accounts DROP CONSTRAINT IF EXISTS accounts_account_type_check;
ALTER TABLE accounts ADD CONSTRAINT accounts_account_type_check
    CHECK (account_type IN ('checking','savings','credit','loan','business'));

-- 1d. Standardize account numbers (PK-BANK → PK99-BANK)
UPDATE accounts
SET account_number = REPLACE(account_number, 'PK-BANK', 'PK99-BANK')
WHERE account_number LIKE '%PK-BANK%';

-- 1e. Standardize profile image paths for users who have none
UPDATE users
SET profile_image = 'profile_pics/' || user_id || '.png'
WHERE profile_image IS NULL;

-- 1f. Support Tickets Table
CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    subject VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    admin_reply TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);


-- ─────────────────────────────────────────────────────────────
-- 2. DROP VIEWS THAT DEPEND ON ALTERED COLUMNS
-- ─────────────────────────────────────────────────────────────
DROP VIEW IF EXISTS active_accounts_view CASCADE;
DROP VIEW IF EXISTS recent_audit_view CASCADE;
DROP VIEW IF EXISTS overdue_loans_view CASCADE;
DROP VIEW IF EXISTS open_fraud_alerts_view CASCADE;


-- ─────────────────────────────────────────────────────────────
-- 3. RECREATE ALL VIEWS (from views.sql)
-- ─────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW active_accounts_view AS
SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    a.account_number,
    a.account_type,
    a.balance,
    a.status,
    u.is_active,
    u.user_id,
    u.last_login,
    u.profile_image,
    (SELECT attempt_time FROM login_attempts
     WHERE user_id = u.user_id AND success = TRUE
     ORDER BY attempt_time DESC OFFSET 1 LIMIT 1) AS previous_login,
    c.kyc_status,
    c.credit_score,
    a.interest_rate,
    a.overdraft_limit,
    a.currency
FROM users u
JOIN customers c ON u.user_id = c.user_id
JOIN accounts a ON c.customer_id = a.customer_id
WHERE a.status = 'active';

CREATE OR REPLACE VIEW recent_audit_view AS
SELECT
    l.log_id,
    COALESCE(u.username, 'System') AS actor,
    l.action,
    l.table_name,
    l.log_time
FROM audit_log l
LEFT JOIN users u ON l.user_id = u.user_id
ORDER BY l.log_time DESC
LIMIT 20;

CREATE OR REPLACE VIEW overdue_loans_view AS
SELECT
    l.loan_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    l.loan_type,
    l.outstanding_balance,
    l.maturity_date,
    CURRENT_DATE - l.maturity_date AS days_overdue
FROM loans l
JOIN customers c ON l.customer_id = c.customer_id
WHERE l.maturity_date < CURRENT_DATE AND l.status = 'active';

CREATE OR REPLACE VIEW open_fraud_alerts_view AS
SELECT
    fa.alert_id,
    fa.alert_type,
    fa.severity,
    fa.created_at,
    a.account_number,
    t.description AS recipient_info,
    t.amount,
    c.user_id
FROM fraud_alerts fa
JOIN accounts a ON fa.account_id = a.account_id
JOIN customers c ON a.customer_id = c.customer_id
LEFT JOIN transactions t ON fa.transaction_id = t.transaction_id
WHERE fa.status = 'open'
ORDER BY fa.created_at DESC;


-- ─────────────────────────────────────────────────────────────
-- 4. TRIGGER FIXES (Unified balance management with recursion guard)
-- ─────────────────────────────────────────────────────────────

-- Drop all old conflicting triggers first
DROP TRIGGER IF EXISTS trg_update_balance ON transactions;
DROP TRIGGER IF EXISTS trg_update_balance_on_approve ON transactions;
DROP TRIGGER IF EXISTS trg_balance_management ON transactions;

-- Replace the handle_transaction_balance function with the final version
CREATE OR REPLACE FUNCTION handle_transaction_balance()
RETURNS TRIGGER AS $$
DECLARE
    v_new_balance DECIMAL(15,2);
BEGIN
    -- Recursion protection: skip if triggered by internal balance_after UPDATE
    IF (pg_trigger_depth() > 1) THEN
        RETURN NEW;
    END IF;

    -- Process only when status becomes/is 'completed'
    IF (TG_OP = 'INSERT' AND NEW.status = 'completed') OR
       (TG_OP = 'UPDATE' AND OLD.status = 'pending' AND NEW.status = 'completed') THEN

        -- Update account balance
        IF NEW.transaction_type = 'deposit' THEN
            UPDATE accounts SET balance = balance + NEW.amount
            WHERE account_id = NEW.account_id
            RETURNING balance INTO v_new_balance;
        ELSIF NEW.transaction_type IN ('withdrawal', 'transfer', 'payment', 'fee') THEN
            UPDATE accounts SET balance = balance - NEW.amount
            WHERE account_id = NEW.account_id
            RETURNING balance INTO v_new_balance;
        END IF;

        -- Capture balance snapshot on the transaction
        IF v_new_balance IS NOT NULL THEN
            UPDATE transactions SET balance_after = v_new_balance
            WHERE transaction_id = NEW.transaction_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Recreate unified trigger
CREATE TRIGGER trg_balance_management
AFTER INSERT OR UPDATE ON transactions
FOR EACH ROW EXECUTE FUNCTION handle_transaction_balance();

-- 4b. Intercept large transactions (Admin-Approved Cash Deposit Bypass)
CREATE OR REPLACE FUNCTION intercept_large_transaction()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.amount >= 10000 AND NEW.description != 'Admin-Approved Cash Deposit' THEN
        NEW.status := 'pending';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ─────────────────────────────────────────────────────────────
-- 5. BACKFILL balance_after FOR EXISTING COMPLETED TRANSACTIONS
-- ─────────────────────────────────────────────────────────────
UPDATE transactions t
SET balance_after = a.balance
FROM accounts a
WHERE t.account_id = a.account_id
  AND t.status = 'completed'
  AND t.balance_after IS NULL;


-- Done!
SELECT 'All patches applied successfully.' AS result;
