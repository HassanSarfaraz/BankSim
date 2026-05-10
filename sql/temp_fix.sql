-- Fix transfer_funds procedure
CREATE OR REPLACE PROCEDURE transfer_funds(
    p_from_account BIGINT,
    p_to_account BIGINT,
    p_amount DECIMAL,
    p_description TEXT
)
LANGUAGE plpgsql AS $$
DECLARE
    v_balance DECIMAL;
BEGIN
    SELECT balance INTO v_balance FROM accounts
    WHERE account_id = p_from_account FOR UPDATE;

    IF v_balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient funds: balance is %, need %', v_balance, p_amount;
    END IF;

    -- Debit sender (balance trigger deducts if status=completed)
    INSERT INTO transactions(account_id, transaction_type, amount, description, transaction_date)
    VALUES (p_from_account, 'withdrawal', p_amount, p_description, NOW());

    -- Credit receiver (balance trigger adds if status=completed)
    -- For large amounts the intercept trigger sets both to status=pending
    INSERT INTO transactions(account_id, transaction_type, amount, description, transaction_date)
    VALUES (p_to_account, 'deposit', p_amount, p_description, NOW());
END;
$$;

-- Fix balance trigger to handle deposit/withdrawal correctly
CREATE OR REPLACE FUNCTION update_balance_after_txn()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' THEN
        IF NEW.transaction_type = 'deposit' THEN
            UPDATE accounts SET balance = balance + NEW.amount
            WHERE account_id = NEW.account_id;
        ELSIF NEW.transaction_type IN ('withdrawal', 'transfer', 'payment', 'fee') THEN
            UPDATE accounts SET balance = balance - NEW.amount
            WHERE account_id = NEW.account_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Fix approval trigger - same logic for updates
CREATE OR REPLACE FUNCTION update_balance_after_txn_update()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status = 'pending' AND NEW.status = 'completed' THEN
        IF NEW.transaction_type = 'deposit' THEN
            UPDATE accounts SET balance = balance + NEW.amount
            WHERE account_id = NEW.account_id;
        ELSIF NEW.transaction_type IN ('withdrawal', 'transfer', 'payment', 'fee') THEN
            UPDATE accounts SET balance = balance - NEW.amount
            WHERE account_id = NEW.account_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;










-- 1. Standardize existing account numbers
UPDATE accounts SET account_number = REPLACE(account_number, 'PK-BANK', 'PK99-BANK');

-- 2. Standardize profile image paths for all users
UPDATE users SET profile_image = 'profile_pics/' || user_id || '.png' WHERE profile_image IS NULL OR profile_image = '';

-- 3. Backfill previous_login for users who have logged in multiple times but have NULL in the column
UPDATE users u
SET previous_login = (
    SELECT attempt_time 
    FROM login_attempts 
    WHERE user_id = u.user_id AND success = TRUE 
    ORDER BY attempt_time DESC 
    OFFSET 1 LIMIT 1
)
WHERE previous_login IS NULL;

-- 4. Recreate views to use optimized logic (relying on u.previous_login)
DROP VIEW IF EXISTS active_accounts_view CASCADE;
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
    u.previous_login,
    c.kyc_status,
    c.credit_score,
    a.interest_rate,
    a.overdraft_limit,
    a.currency
FROM users u
JOIN customers c ON u.user_id = c.user_id
JOIN accounts a ON c.customer_id = a.customer_id
WHERE a.status = 'active';



-- Clear all stale/manually inserted data that's causing sequence conflicts
TRUNCATE TABLE support_tickets RESTART IDENTITY CASCADE;
TRUNCATE TABLE deposit_requests RESTART IDENTITY CASCADE;
TRUNCATE TABLE fraud_alerts RESTART IDENTITY CASCADE;




-- 1. Force delete all data from problematic tables
DELETE FROM support_tickets;
DELETE FROM deposit_requests;
DELETE FROM fraud_alerts;

-- 2. Force reset the sequences to 1
ALTER SEQUENCE support_tickets_ticket_id_seq RESTART WITH 1;
ALTER SEQUENCE deposit_requests_request_id_seq RESTART WITH 1;
ALTER SEQUENCE fraud_alerts_alert_id_seq RESTART WITH 1;

-- 3. Verify they are empty (should return 0)
SELECT count(*) FROM support_tickets;
SELECT count(*) FROM deposit_requests;


